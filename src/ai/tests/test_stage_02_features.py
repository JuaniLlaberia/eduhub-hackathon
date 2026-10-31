"""
Stage 02: post selection, deterministic features and the performance score (D2: geometric mean of relative ER
and relative reach). Pure functions, no LLM.
"""
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
import pytest
from eduhub_ai.features.deterministic import extract_deterministic, hour_block
from eduhub_ai.features.scoring import score_posts
from eduhub_ai.features.selection import MIN_SCORABLE_POSTS, select_scorable
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.metrics import length_bucket
from eduhub_shared.models import AccountSnapshot, MediaType, Post, PostKind, PostMetrics, Trend

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
REAL_DATA = Path(__file__).parent / "data" / "real"

def make_post(
    post_id: str = "1",
    text: str = "Hola",
    kind: PostKind = PostKind.ORIGINAL,
    age: timedelta = timedelta(days=3),
    impressions: int | None = 1000,
    likes: int = 10,
    created_at: datetime | None = None,
    media: list[MediaType] | None = None,
) -> Post:
    return Post(
        id=post_id,
        author_handle="demo",
        text=text,
        created_at=created_at or NOW - age,
        url=f"https://x.com/demo/status/{post_id}",
        kind=kind,
        media=media or [],
        metrics=PostMetrics(impressions=impressions, likes=likes, reposts=0, quotes=0, replies=0, bookmarks=0),
    )

def trend(name: str) -> Trend:
    return Trend(name=name, observed_at=NOW)

# ---------- selection ----------
def test_selection_excludes_with_reasons_and_keeps_originals_and_quotes():
    posts = [
        make_post("reply", kind=PostKind.REPLY),
        make_post("repost", kind=PostKind.REPOST),
        make_post("recent", age=timedelta(hours=10)),
        make_post("no_views", impressions=None),
        make_post("zero_views", impressions=0),
        make_post("original"),
        make_post("quote", kind=PostKind.QUOTE),
    ]
    result = select_scorable(posts, NOW)
    assert [p.id for p in result.scorable] == ["original", "quote"]
    assert result.excluded == {
        "reply": "reply",
        "repost": "repost",
        "recent": "too_recent",
        "no_views": "no_impressions",
        "zero_views": "no_impressions",
    }

def test_selection_boundary_at_exactly_min_age_is_scorable():
    at_boundary = make_post("edge", age=timedelta(hours=48))
    just_inside = make_post("inside", age=timedelta(hours=48) - timedelta(seconds=1))
    result = select_scorable([at_boundary, just_inside], NOW)
    assert [p.id for p in result.scorable] == ["edge"]
    assert result.excluded == {"inside": "too_recent"}

def test_selection_custom_min_age_and_preserves_order():
    posts = [make_post(str(i), age=timedelta(hours=10 + i)) for i in range(5)]
    result = select_scorable(posts, NOW, min_age=timedelta(hours=12))
    assert [p.id for p in result.scorable] == ["2", "3", "4"]

def test_min_scorable_posts_constant():
    assert MIN_SCORABLE_POSTS == 20

# ---------- time features ----------
def test_local_hour_and_weekday_in_argentina():
    post = make_post(created_at=datetime(2026, 10, 28, 23, 30, tzinfo=UTC))
    features = extract_deterministic(post, [])
    assert features.hour_local == 20
    assert features.weekday == 2

@pytest.mark.parametrize(("hour", "block"), [
    (0, "madrugada"), (5, "madrugada"),
    (6, "mañana"), (11, "mañana"),
    (12, "mediodía"), (14, "mediodía"),
    (15, "tarde"), (18, "tarde"),
    (19, "noche"), (20, "noche"), (23, "noche"),
])
def test_hour_block(hour, block):
    assert hour_block(hour) == block

@pytest.mark.parametrize("hour", [-1, 24])
def test_hour_block_out_of_range_raises(hour):
    with pytest.raises(ValueError):
        hour_block(hour)

# ---------- deterministic features ----------
@pytest.mark.parametrize("text", ["Hola", "x" * 150, "y" * 250])
def test_length_bucket_matches_shared_metrics(text):
    features = extract_deterministic(make_post(text=text), [])
    assert features.char_count == len(text)
    assert features.length_bucket == length_bucket(len(text))

def test_counts_media_link_hashtags_mentions():
    post = make_post(text="Mirá esto con @ana y @beto #ahorro", media=[MediaType.VIDEO, MediaType.PHOTO])
    post = post.model_copy(update={"has_link": True, "hashtags": ["ahorro"], "mentions": ["ana", "beto"]})
    features = extract_deterministic(post, [])
    assert features.word_count == 7
    assert features.media_type == MediaType.VIDEO
    assert features.has_link is True
    assert features.hashtag_count == 1
    assert features.mention_count == 2

def test_text_only_post_has_no_media_type():
    assert extract_deterministic(make_post(), []).media_type is None

@pytest.mark.parametrize(("text", "expected"), [
    ("¿Ahorrás?", True),
    ("¿Cuánto cobraste de aguinaldo", True),
    ("Esto es una afirmación.", False),
    ("Mirá esto https://example.com/a?b=1", False),
])
def test_question_detection(text, expected):
    assert extract_deterministic(make_post(text=text), []).is_question is expected

@pytest.mark.parametrize(("text", "expected"), [
    ("Qué día 🔥", True),
    ("Me encanta ❤️", True),
    ("Vamos ✅", True),
    ("Arriba 🇦🇷", True),
    ("Sin emojis, solo texto: 100% (ok)", False),
])
def test_emoji_detection(text, expected):
    assert extract_deterministic(make_post(text=text), []).has_emoji is expected

def test_trend_match_is_case_and_accent_insensitive_without_hash():
    features = extract_deterministic(make_post(text="Por fin cobré el aguinaldo"), [trend("#Aguinaldo")])
    assert features.matches_trend is True
    features = extract_deterministic(make_post(text="La MUSICA de hoy"), [trend("Música")])
    assert features.matches_trend is True

def test_trend_match_multiword_and_whole_words_only():
    trends = [trend("Black Friday"), trend("Paro")]
    assert extract_deterministic(make_post(text="Ofertas de black friday!"), trends).matches_trend is True
    assert extract_deterministic(make_post(text="Te comparo los precios"), trends).matches_trend is False

def test_trend_match_is_none_without_trends():
    assert extract_deterministic(make_post(text="aguinaldo"), []).matches_trend is None

def test_semantic_fields_are_none():
    features = extract_deterministic(make_post(text="¿Ahorrás? 🔥 #ahorro"), [trend("ahorro")])
    assert features.topic is None
    assert features.tone is None
    assert features.sentiment is None
    assert features.hook is None
    assert features.cta is None

# ---------- score ----------
def test_median_post_scores_one_and_double_er_scores_sqrt_two():
    posts = [make_post(str(i), impressions=1000, likes=likes) for i, likes in enumerate([10, 20, 20, 20, 40])]
    scores = score_posts(posts)
    assert scores["1"] == pytest.approx(1.0)
    assert scores["4"] == pytest.approx(math.sqrt(2))
    assert scores["0"] == pytest.approx(math.sqrt(0.5))

def test_double_reach_at_median_er_scores_sqrt_two():
    posts = [make_post(str(i), impressions=imp, likes=imp // 50) for i, imp in enumerate([500, 1000, 1000, 1000, 2000])]
    scores = score_posts(posts)
    assert scores["1"] == pytest.approx(1.0)
    assert scores["4"] == pytest.approx(math.sqrt(2))

def test_missing_or_zero_impressions_score_none_and_are_ignored_by_medians():
    posts = [
        make_post("a", impressions=1000, likes=20),
        make_post("b", impressions=None, likes=500),
        make_post("c", impressions=0, likes=500),
    ]
    scores = score_posts(posts)
    assert scores == {"a": pytest.approx(1.0), "b": None, "c": None}

def test_zero_median_engagement_gives_none():
    posts = [make_post(str(i), impressions=1000, likes=0) for i in range(3)]
    assert score_posts(posts) == {"0": None, "1": None, "2": None}

def test_zero_engagement_post_scores_zero_and_all_scores_non_negative():
    posts = [make_post(str(i), impressions=1000 + 100 * i, likes=likes) for i, likes in enumerate([0, 5, 20, 40, 3])]
    scores = score_posts(posts)
    assert scores["0"] == 0.0
    assert all(s is not None and s >= 0 for s in scores.values())

def test_score_posts_returns_every_post_and_empty_input():
    posts = [make_post(str(i)) for i in range(4)]
    assert set(score_posts(posts)) == {"0", "1", "2", "3"}
    assert score_posts([]) == {}

def test_viral_outlier_barely_moves_other_scores():
    base = [make_post(str(i), impressions=1000 + 100 * i, likes=(1000 + 100 * i) // 50) for i in range(9)]
    viral = make_post("viral", impressions=1_000_000, likes=50_000)
    before = score_posts(base)
    after = score_posts([*base, viral])
    for post in base:
        assert after[post.id] == pytest.approx(before[post.id], rel=0.05)
    assert after["viral"] > 10

# ---------- features package stays LLM-free ----------
def test_features_package_has_no_llm_imports():
    package = Path(__file__).parents[1] / "eduhub_ai" / "features"
    sources = [p.read_text(encoding="utf-8") for p in package.glob("*.py")]
    assert sources
    for source in sources:
        assert "eduhub_ai.llm" not in source
        assert "openai" not in source

# ---------- snapshots ----------
def check_snapshot(snapshot: AccountSnapshot) -> None:
    features = [extract_deterministic(p, snapshot.trends) for p in snapshot.posts]
    assert len(features) == len(snapshot.posts)
    selection = select_scorable(snapshot.posts, snapshot.collected_at)
    assert len(selection.scorable) + len(selection.excluded) == len(snapshot.posts)
    assert len(selection.scorable) >= MIN_SCORABLE_POSTS
    scores = score_posts(selection.scorable)
    assert set(scores) == {p.id for p in selection.scorable}
    assert all(scores[p.id] is not None for p in selection.scorable)

def test_shared_fixture_snapshot():
    check_snapshot(load_snapshot())

@pytest.mark.skipif(not list(REAL_DATA.glob("*.json")), reason="real snapshots are git-ignored; copy them locally")
@pytest.mark.parametrize("path", sorted(REAL_DATA.glob("*.json")), ids=lambda p: p.stem)
def test_real_snapshots(path):
    check_snapshot(AccountSnapshot.model_validate_json(path.read_text(encoding="utf-8")))
