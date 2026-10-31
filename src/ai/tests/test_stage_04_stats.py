"""
Stage 04: stats engine (KPIs, heatmap, hour blocks, best slots, segments with bootstrap CIs, significance).
Pure and deterministic: no clock, seeded randomness.
"""
import statistics
from datetime import UTC, datetime, timedelta
import numpy as np
import pytest
from eduhub_ai.features import extract_deterministic, score_posts, select_scorable
from eduhub_ai.stats.kpis import build_kpis
from eduhub_ai.stats.segments import SegmentDetail, build_segments, segment_details
from eduhub_ai.stats.significance import bootstrap_ci, is_significant, mann_whitney
from eduhub_ai.stats.timing import best_time_slots, build_heatmap, hour_block_stats
from eduhub_shared import fakes
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.metrics import aggregate_rates, compute_rates
from eduhub_shared.models import AnalyzedPost, Post, PostKind, PostMetrics, SegmentDimension, TimeSlotStat

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
# 2026-10-26 is a Monday; 15:00 UTC = 12:00 in Argentina.
MONDAY_NOON_AR = datetime(2026, 10, 26, 15, 0, tzinfo=UTC)

def make_post(i: int, when: datetime | None = None, kind: PostKind = PostKind.ORIGINAL,
              impressions: int | None = 1000, likes: int = 20) -> Post:
    return Post(
        id=f"p{i}",
        author_handle="demo",
        text=f"Post {i}",
        created_at=when or NOW - timedelta(days=3, hours=i),
        url=f"https://x.com/demo/status/{i}",
        kind=kind,
        metrics=PostMetrics(impressions=impressions, likes=likes, reposts=0, quotes=0, replies=0, bookmarks=0),
    )

def analyzed(post: Post, score: float | None, **labels: str | None) -> AnalyzedPost:
    features = extract_deterministic(post, []).model_copy(update=labels)
    return AnalyzedPost(post=post, features=features, rates=compute_rates(post.metrics), score=score)

def fixture_analyzed() -> list[AnalyzedPost]:
    # The shared fixture, scored with stage 02, with topic = first hashtag (the fixture's built-in story).
    snapshot = load_snapshot()
    scores = score_posts(select_scorable(snapshot.posts, snapshot.collected_at).scorable)
    return [analyzed(p, scores.get(p.id), topic=p.hashtags[0] if p.hashtags else None) for p in snapshot.posts]

def detail(details: list[SegmentDetail], dimension: str, value: str) -> SegmentDetail:
    return next(d for d in details if d.dimension == dimension and d.value == value)

# ---------- KPIs ----------
def test_kpis_match_the_shared_formulas_on_the_fixture():
    posts = load_snapshot().posts
    assert build_kpis(posts) == fakes.build_kpis(posts)

def test_kpis_rates_are_aggregated_and_empty_input_is_safe():
    posts = [make_post(0, impressions=1000, likes=10), make_post(1, impressions=3000, likes=90),
             make_post(2, impressions=None, likes=500)]
    kpis = build_kpis(posts)
    assert kpis.post_count == 3
    assert kpis.median_impressions == 2000.0
    assert kpis.rates == aggregate_rates(p.metrics for p in posts)
    assert kpis.rates.engagement_rate == pytest.approx(100 / 4000)
    empty = build_kpis([])
    assert empty.post_count == 0
    assert empty.median_impressions is None

# ---------- heatmap and timing ----------
def test_heatmap_uses_scorable_posts_with_unique_slots_and_median_scores():
    posts = [
        analyzed(make_post(0, MONDAY_NOON_AR), 1.0),
        analyzed(make_post(1, MONDAY_NOON_AR + timedelta(minutes=20)), 2.0),
        analyzed(make_post(2, MONDAY_NOON_AR + timedelta(minutes=40)), 9.0),
        analyzed(make_post(3, MONDAY_NOON_AR + timedelta(hours=3)), 0.5),
        analyzed(make_post(4, MONDAY_NOON_AR, kind=PostKind.REPLY), None),
    ]
    heatmap = build_heatmap(posts)
    slots = [(s.weekday, s.hour) for s in heatmap]
    assert len(slots) == len(set(slots))
    assert sum(s.post_count for s in heatmap) == 4
    noon = next(s for s in heatmap if (s.weekday, s.hour) == (0, 12))
    assert noon.post_count == 3
    assert noon.avg_score == pytest.approx(2.0)

def test_heatmap_on_fixture_counts_every_scorable_post():
    posts = fixture_analyzed()
    heatmap = build_heatmap(posts)
    assert sum(s.post_count for s in heatmap) == sum(p.score is not None for p in posts)
    for slot in heatmap:
        scores = [p.score for p in posts if p.score is not None
                  and (p.features.weekday, p.features.hour_local) == (slot.weekday, slot.hour)]
        assert slot.avg_score == pytest.approx(statistics.median(scores))

def test_best_slots_at_most_three_and_prefer_slots_with_two_or_more_posts():
    heatmap = [
        TimeSlotStat(weekday=0, hour=9, post_count=1, avg_score=3.0),
        TimeSlotStat(weekday=1, hour=20, post_count=2, avg_score=2.8),
        TimeSlotStat(weekday=2, hour=21, post_count=4, avg_score=1.5),
        TimeSlotStat(weekday=3, hour=8, post_count=3, avg_score=1.2),
        TimeSlotStat(weekday=4, hour=13, post_count=2, avg_score=0.9),
    ]
    best = best_time_slots(heatmap)
    assert len(best) == 3
    assert [(s.weekday, s.hour) for s in best] == [(1, 20), (2, 21), (3, 8)]

def test_best_slots_fall_back_to_single_post_slots_when_nothing_else():
    heatmap = [TimeSlotStat(weekday=0, hour=9, post_count=1, avg_score=3.0),
               TimeSlotStat(weekday=1, hour=9, post_count=1, avg_score=1.0)]
    assert [(s.weekday, s.hour) for s in best_time_slots(heatmap)] == [(0, 9), (1, 9)]

def test_hour_block_stats_group_by_block_and_weekday_vs_weekend():
    saturday_night = datetime(2026, 10, 31, 23, 30, tzinfo=UTC) - timedelta(days=7)  # Sat 20:30 AR
    posts = [analyzed(make_post(i, MONDAY_NOON_AR + timedelta(days=i % 3)), 1.0) for i in range(6)]
    posts += [analyzed(make_post(10 + i, saturday_night + timedelta(minutes=i)), 3.0) for i in range(4)]
    details = hour_block_stats(posts)
    assert detail(details, "hour_block", "mediodía").n == 6
    assert detail(details, "hour_block", "noche").n == 4
    assert detail(details, "day_type", "fin de semana").n == 4
    assert detail(details, "day_type", "semana").n == 6
    assert detail(details, "hour_block_day_type", "noche, fin de semana").median_score == pytest.approx(3.0)

# ---------- segments ----------
def test_segments_one_row_per_present_value_and_none_skipped():
    posts = [
        analyzed(make_post(0), 2.0, topic="ahorro", tone="humor"),
        analyzed(make_post(1), 1.0, topic="ahorro", tone=None),
        analyzed(make_post(2), 0.5, topic="cripto", tone=None),
        analyzed(make_post(3), 0.7, topic=None, tone=None),
    ]
    segments = build_segments(posts)
    keys = [(s.dimension, s.value) for s in segments]
    assert len(keys) == len(set(keys))
    topics = {s.value: s for s in segments if s.dimension == SegmentDimension.TOPIC}
    assert set(topics) == {"ahorro", "cripto"}
    assert topics["ahorro"].post_count == 2
    assert topics["ahorro"].avg_score == pytest.approx(1.5)
    tones = [s for s in segments if s.dimension == SegmentDimension.TONE]
    assert [(s.value, s.post_count) for s in tones] == [("humor", 1)]
    media = [s for s in segments if s.dimension == SegmentDimension.MEDIA_TYPE]
    assert [(s.value, s.post_count) for s in media] == [("text", 4)]

def test_segments_skip_unscorable_posts():
    posts = [analyzed(make_post(0), 1.0, topic="ahorro"),
             analyzed(make_post(1, kind=PostKind.REPLY), None, topic="ahorro")]
    topics = [s for s in build_segments(posts) if s.dimension == SegmentDimension.TOPIC]
    assert topics[0].post_count == 1

def test_hook_and_cta_segments_present_only_when_labeled():
    unlabeled = [analyzed(make_post(i), 1.0) for i in range(4)]
    dimensions = {s.dimension for s in build_segments(unlabeled)}
    assert SegmentDimension.HOOK not in dimensions
    assert SegmentDimension.CTA not in dimensions
    labeled = [analyzed(make_post(i), 1.0 + i, hook="pregunta", cta="guardar") for i in range(4)]
    dimensions = {s.dimension for s in build_segments(labeled)}
    assert SegmentDimension.HOOK in dimensions
    assert SegmentDimension.CTA in dimensions

def test_segments_sorted_best_first_within_dimension():
    posts = [analyzed(make_post(i), score, topic=topic)
             for i, (score, topic) in enumerate([(0.5, "a"), (2.0, "b"), (1.0, "c"), (2.2, "b")])]
    topics = [s.value for s in build_segments(posts) if s.dimension == SegmentDimension.TOPIC]
    assert topics == ["b", "c", "a"]

def test_segment_details_fields():
    posts = [analyzed(make_post(i), 2.0 + 0.01 * i, topic="ahorro") for i in range(10)]
    posts += [analyzed(make_post(20 + i), 1.0 + 0.01 * i, topic="cripto") for i in range(10)]
    ahorro = detail(segment_details(posts), "topic", "ahorro")
    assert ahorro.n == 10
    assert ahorro.median_score == pytest.approx(statistics.median(2.0 + 0.01 * i for i in range(10)))
    assert ahorro.ci_low <= ahorro.median_score <= ahorro.ci_high
    rest_median = statistics.median(1.0 + 0.01 * i for i in range(10))
    assert ahorro.lift_vs_rest == pytest.approx(ahorro.median_score / rest_median)
    assert ahorro.p_value < 0.01

# ---------- bootstrap and significance ----------
def test_bootstrap_is_deterministic_and_contains_the_median():
    values = list(np.random.default_rng(1).lognormal(0, 0.5, 30))
    low, high = bootstrap_ci(values)
    assert (low, high) == bootstrap_ci(values)
    assert low <= statistics.median(values) <= high

def test_bootstrap_ci_narrows_with_more_data():
    rng = np.random.default_rng(2)
    small = list(rng.lognormal(0, 0.5, 10))
    large = list(rng.lognormal(0, 0.5, 300))
    small_low, small_high = bootstrap_ci(small)
    large_low, large_high = bootstrap_ci(large)
    assert large_high - large_low < small_high - small_low

def test_bootstrap_single_value_and_empty():
    assert bootstrap_ci([1.7]) == (1.7, 1.7)
    with pytest.raises(ValueError):
        bootstrap_ci([])

def test_mann_whitney_edge_cases():
    assert mann_whitney([1.0, 1.0, 1.0], [1.0, 1.0, 1.0]) == 1.0
    assert mann_whitney([2.0, 2.1], []) == 1.0
    assert mann_whitney([2.0, 2.1, 2.2, 2.3], [1.0, 1.1, 1.2, 1.3]) < 0.05

def make_group(scores: list[float], topic: str, start: int) -> list[AnalyzedPost]:
    return [analyzed(make_post(start + i), s, topic=topic) for i, s in enumerate(scores)]

def test_clearly_better_group_is_significant():
    posts = make_group([2.0 + 0.02 * i for i in range(10)], "bueno", 0)
    posts += make_group([1.0 + 0.02 * i for i in range(10)], "normal", 100)
    assert is_significant(detail(segment_details(posts), "topic", "bueno"))

def test_group_of_two_is_never_significant():
    posts = make_group([5.0, 6.0], "chico", 0) + make_group([1.0 + 0.01 * i for i in range(20)], "normal", 100)
    assert not is_significant(detail(segment_details(posts), "topic", "chico"))

def test_identical_distributions_are_not_significant():
    scores = [0.6, 0.8, 0.9, 1.0, 1.0, 1.1, 1.2, 1.4]
    posts = make_group(scores, "a", 0) + make_group(scores, "b", 100)
    details = segment_details(posts)
    assert not is_significant(detail(details, "topic", "a"))
    assert not is_significant(detail(details, "topic", "b"))

def test_significance_thresholds_are_configurable():
    big = SegmentDetail(dimension="topic", value="x", n=5, median_score=1.5, ci_low=1.2, ci_high=1.9,
                        lift_vs_rest=1.6, p_value=0.5)
    assert is_significant(big)
    assert not is_significant(big, min_n=6)
    straddles = SegmentDetail(dimension="topic", value="y", n=5, median_score=1.2, ci_low=0.9, ci_high=1.5,
                              lift_vs_rest=1.3, p_value=0.05)
    assert is_significant(straddles)
    assert not is_significant(straddles, alpha=0.01)

# ---------- the fixture's built-in story ----------
def test_fixture_presupuesto_best_and_significant_tarjetas_worst():
    posts = fixture_analyzed()
    topics = [s for s in build_segments(posts) if s.dimension == SegmentDimension.TOPIC]
    assert topics[0].value == "presupuesto"
    assert topics[-1].value == "tarjetas"
    assert is_significant(detail(segment_details(posts), "topic", "presupuesto"))

def test_stats_are_deterministic():
    posts = fixture_analyzed()
    assert segment_details(posts) == segment_details(posts)
    assert hour_block_stats(posts) == hour_block_stats(posts)
    assert build_heatmap(posts) == build_heatmap(posts)
