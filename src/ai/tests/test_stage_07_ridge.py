"""
Stage 07: per-account ridge pattern model on log(score): adjusted effects with bootstrap CIs, pairwise accuracy,
the data-sufficiency rule, and its integration into the evidence pack and the analyzer.
"""
import asyncio
import math
import statistics
import time
from datetime import UTC, datetime
import numpy as np
from eduhub_ai.analyzer import HybridAnalyzer
from eduhub_ai.config import load_settings
from eduhub_ai.features import extract_deterministic
from eduhub_ai.insights import build_evidence, template_texts
from eduhub_ai.insights.grounding import extract_numbers, ungrounded
from eduhub_ai.patterns.base import Effect, can_fit, feature_row
from eduhub_ai.patterns.evaluation import pairwise_accuracy
from eduhub_ai.patterns.integration import adjust_confidence, effect_items, fit_from_posts, fit_from_report
from eduhub_ai.patterns.ridge import RidgePatternModel
from eduhub_ai.stats import best_time_slots, build_heatmap, build_kpis
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.models import AnalysisReport, MediaType, Post, PostMetrics
from eduhub_shared.testing import check_analyzer

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
SETTINGS = load_settings({})

def photo_data(n: int = 120, seed: int = 0, effect: float = 1.5, noise: float = 0.3):
    rng = np.random.default_rng(seed)
    rows, scores = [], []
    for _ in range(n):
        photo = rng.random() < 0.4
        rows.append({"media_type": "photo" if photo else "text", "has_emoji": bool(rng.random() < 0.5),
                     "topic": str(rng.choice(["a", "b", "c"]))})
        scores.append(math.exp((math.log(effect) if photo else 0.0) + rng.normal(0, noise)))
    return rows, scores

def confounded_data(n: int = 200, seed: int = 1):
    rng = np.random.default_rng(seed)
    rows, scores = [], []
    for _ in range(n):
        presupuesto = rng.random() < 0.4
        noche = rng.random() < (0.85 if presupuesto else 0.2)
        rows.append({"topic": "presupuesto" if presupuesto else "ahorro", "hour_block": "noche" if noche else "tarde"})
        scores.append(math.exp((math.log(2.0) if presupuesto else 0.0) + rng.normal(0, 0.3)))
    return rows, scores

def noise_data(n: int = 120, seed: int = 2):
    rng = np.random.default_rng(seed)
    rows = [{"media_type": str(rng.choice(["photo", "text"])), "topic": str(rng.choice(["a", "b"]))} for _ in range(n)]
    return rows, [float(math.exp(rng.normal(0, 0.5))) for _ in range(n)]

def effect(effects: list[Effect], feature: str, value: str) -> Effect:
    return next(e for e in effects if (e.feature, e.value) == (feature, value))

def fitted(rows, scores) -> RidgePatternModel:
    model = RidgePatternModel()
    model.fit(rows, scores)
    return model

def fixture_report() -> AnalysisReport:
    return asyncio.run(HybridAnalyzer(SETTINGS, None, clock=lambda: NOW).analyze(load_snapshot()))

# ---------- effects ----------
def test_true_photo_effect_is_recovered_with_a_ci_excluding_one():
    effects = fitted(*photo_data()).effects()
    photo = effect(effects, "media_type", "photo")
    assert photo.baseline == "text"
    assert abs(photo.multiplier - 1.5) <= 0.2
    assert photo.ci_low > 1.0
    assert photo.ci_low <= photo.multiplier <= photo.ci_high
    assert photo.n == sum(r["media_type"] == "photo" for r in photo_data()[0])
    emoji = effect(effects, "has_emoji", "sí")
    assert emoji.ci_low <= 1.0 <= emoji.ci_high

def test_ridge_separates_confounded_effects_that_segment_stats_mix_up():
    rows, scores = confounded_data()
    noche_scores = [s for r, s in zip(rows, scores, strict=True) if r["hour_block"] == "noche"]
    tarde_scores = [s for r, s in zip(rows, scores, strict=True) if r["hour_block"] == "tarde"]
    segment_lift = statistics.median(noche_scores) / statistics.median(tarde_scores)
    assert segment_lift > 1.3
    effects = fitted(rows, scores).effects()
    presupuesto = effect(effects, "topic", "presupuesto")
    noche = effect(effects, "hour_block", "noche")
    assert presupuesto.multiplier > noche.multiplier
    assert presupuesto.ci_low > 1.0
    assert 0.8 <= noche.multiplier <= 1.25
    assert noche.multiplier < segment_lift

def test_rare_levels_are_merged_into_otros_or_dropped():
    rows, scores = photo_data()
    rows = [dict(r) for r in rows]
    rows[0]["topic"], rows[1]["topic"] = "rarísimo", "rarísimo"
    effects = fitted(rows, scores).effects()
    assert not any(e.value == "rarísimo" for e in effects)
    assert all(e.n >= 3 for e in effects)

def test_predict_favours_the_positive_effect():
    model = fitted(*photo_data())
    photo = model.predict({"media_type": "photo", "has_emoji": False, "topic": "a"})
    text = model.predict({"media_type": "text", "has_emoji": False, "topic": "a"})
    assert photo > text > 0
    assert model.predict({"media_type": "nunca visto", "topic": "zzz"}) > 0

def test_effects_are_deterministic_and_fast_for_200_posts():
    rows, scores = photo_data(n=200)
    started = time.perf_counter()
    first = fitted(rows, scores).effects()
    assert time.perf_counter() - started < 2.0
    assert first == fitted(rows, scores).effects()

# ---------- sufficiency ----------
def test_can_fit_needs_thirty_posts_and_a_usable_feature():
    rows, scores = photo_data(n=120)
    assert not can_fit(rows[:20], scores[:20])
    assert can_fit(rows[:40], scores[:40])
    unique = [{"topic": f"t{i}"} for i in range(40)]
    assert not can_fit(unique, scores[:40])

# ---------- evaluation ----------
def test_pairwise_accuracy_is_chance_on_noise_and_high_on_real_effects():
    noise = pairwise_accuracy(RidgePatternModel, *noise_data())
    assert 0.4 <= noise <= 0.6
    signal = pairwise_accuracy(RidgePatternModel, *photo_data(effect=2.0))
    assert signal > 0.6
    assert signal == pairwise_accuracy(RidgePatternModel, *photo_data(effect=2.0))

# ---------- feature rows ----------
def test_feature_row_from_post_features():
    post = Post(id="1", author_handle="demo", text="¿Hola? 🔥", url="https://x.com/demo/status/1",
                created_at=datetime(2026, 10, 24, 23, 30, tzinfo=UTC), media=[MediaType.PHOTO],
                hashtags=["a", "b"], metrics=PostMetrics(impressions=10, likes=1, reposts=0, quotes=0, replies=0,
                                                         bookmarks=0))
    features = extract_deterministic(post, []).model_copy(update={"topic": "ahorro", "hook": "pregunta"})
    row = feature_row(features)
    assert row["topic"] == "ahorro"
    assert row["hook"] == "pregunta"
    assert "tone" not in row
    assert row["media_type"] == "photo"
    assert row["hour_block"] == "noche"
    assert row["weekend"] is True
    assert row["is_question"] is True
    assert row["has_emoji"] is True
    assert row["hashtags"] == "2+"
    assert "matches_trend" not in row

# ---------- integration ----------
def test_fit_from_report_and_from_posts():
    report = fixture_report()
    assert fit_from_report(report) is not None
    few = [p for p in report.posts if p.score is not None][:25]
    assert fit_from_posts(few) is None

def test_effect_items_are_grounded_in_the_evidence_pack():
    report = fixture_report()
    model = fit_from_report(report)
    items = effect_items(model, report.posts)
    assert items
    assert all(i.id.startswith("model:") and i.kind == "pattern" for i in items)
    assert all(i.confidence is not None and 0 <= i.confidence <= 1 for i in items)
    pack = build_evidence(report.profile, build_kpis([p.post for p in report.posts]), report.posts,
                          best_time_slots(build_heatmap(report.posts)), pattern_effects=items)
    assert pack.pattern_effects == items
    for item in items:
        assert extract_numbers(item.value) <= pack.allowed_numbers
        assert pack.item(item.id) == item
    texts = template_texts(pack)
    assert all(ungrounded(i.description, pack.allowed_numbers) == set() for i in texts.insights)

def test_agreeing_effects_raise_finding_confidence():
    report = fixture_report()
    model = fit_from_report(report)
    pack = build_evidence(report.profile, build_kpis([p.post for p in report.posts]), report.posts,
                          best_time_slots(build_heatmap(report.posts)))
    adjusted = adjust_confidence(pack, model)
    before = pack.item("seg:topic:presupuesto")
    after = adjusted.item("seg:topic:presupuesto")
    assert after.confidence == min(1.0, round(before.confidence + 0.1, 2))
    assert adjusted.allowed_numbers == pack.allowed_numbers

async def test_analyzer_skips_the_model_on_small_accounts_and_stays_valid():
    snapshot = load_snapshot()
    small = snapshot.model_copy(update={"posts": snapshot.posts[:26]})
    analyzer = HybridAnalyzer(SETTINGS, None, clock=lambda: NOW)
    report = await check_analyzer(analyzer, small)
    assert sum(p.score is not None for p in report.posts) == 25
    assert analyzer.pattern_model(report.posts) is None
    full = await analyzer.analyze(snapshot)
    assert analyzer.pattern_model(full.posts) is not None
