"""
Stage 05: insight writer. Evidence pack (computed, pre-formatted es-AR numbers) → one LLM call → grounded
Insight / Recommendation / explanations / summary, with template fallbacks. All LLM calls are scripted.
"""
import json
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from eduhub_ai.config import load_settings
from eduhub_ai.features import extract_deterministic, score_posts, select_scorable
from eduhub_ai.insights.evidence import EvidencePack, build_evidence
from eduhub_ai.insights.fallback import template_texts
from eduhub_ai.insights.grounding import extract_numbers, ungrounded
from eduhub_ai.insights.prompts import WRITER_SYSTEM
from eduhub_ai.insights.writer import MAX_INSIGHTS, WriterResponse, write_texts
from eduhub_ai.llm.client import LLMCall, LLMError
from eduhub_ai.llm.scripted import ScriptedLLMClient
from eduhub_ai.stats import best_time_slots, build_heatmap, build_kpis
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.metrics import compute_rates
from eduhub_shared.models import (
    AccountProfile,
    AnalyzedPost,
    Insight,
    InsightCategory,
    Post,
    PostMetrics,
    Recommendation,
)

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
SETTINGS = load_settings({})
PROFILE = AccountProfile(handle="demo", display_name="Demo", followers_count=1000, following_count=10, posts_count=50)

def make_post(i: int, impressions: int = 1000) -> Post:
    return Post(
        id=f"p{i}",
        author_handle="demo",
        text=f"Post {i}",
        created_at=NOW - timedelta(days=3, hours=7 * i),
        url=f"https://x.com/demo/status/{i}",
        metrics=PostMetrics(impressions=impressions, likes=20, reposts=0, quotes=0, replies=0, bookmarks=0),
    )

def analyzed(i: int, score: float, topic: str) -> AnalyzedPost:
    post = make_post(i)
    features = extract_deterministic(post, []).model_copy(update={"topic": topic})
    return AnalyzedPost(post=post, features=features, rates=compute_rates(post.metrics), score=score)

def synthetic_posts() -> list[AnalyzedPost]:
    posts = [analyzed(i, 2.0 + 0.02 * i, "bueno") for i in range(10)]
    posts += [analyzed(100 + i, 0.8 + 0.04 * i, "normal") for i in range(10)]
    posts += [analyzed(200 + i, 5.0 + i, "chico") for i in range(2)]
    return posts

def make_pack(posts: list[AnalyzedPost] | None = None) -> EvidencePack:
    posts = posts or synthetic_posts()
    kpis = build_kpis([p.post for p in posts])
    return build_evidence(PROFILE, kpis, posts, best_time_slots(build_heatmap(posts)))

def fixture_pack() -> EvidencePack:
    snapshot = load_snapshot()
    scores = score_posts(select_scorable(snapshot.posts, snapshot.collected_at).scorable)
    posts = []
    for p in snapshot.posts:
        features = extract_deterministic(p, snapshot.trends).model_copy(update={"topic": p.hashtags[0]})
        posts.append(AnalyzedPost(post=p, features=features, rates=compute_rates(p.metrics), score=scores.get(p.id)))
    kpis = build_kpis(snapshot.posts)
    return build_evidence(snapshot.profile, kpis, posts, best_time_slots(build_heatmap(posts)))

def insight_json(pack: EvidencePack, evidence_id: str, description: str | None = None,
                 related: list[str] | None = None) -> dict:
    item = pack.item(evidence_id)
    return {
        "category": item.category.value,
        "title": f"Lo que mejor te funciona: {item.label}",
        "description": description or (
            f"Rinde {item.numbers['mediana']} tu post típico en {item.numbers['posts']} posts."
        ),
        "evidence_ids": [evidence_id],
        "impact": "high",
        "related_post_ids": related or [],
    }

def response_json(pack: EvidencePack, insights: list[dict], recommendations: list[dict] | None = None,
                  explanations: list[dict] | None = None,
                  summary: str = "Tu cuenta tiene un tema que rinde mucho.") -> str:
    recs = recommendations if recommendations is not None else [
        {"category": i["category"], "action": "Publicá más de esto.", "rationale": "Es lo que mejor rinde.",
         "priority": n + 1, "insight_index": [n]}
        for n, i in enumerate(insights)
    ]
    return json.dumps({"insights": insights, "recommendations": recs, "explanations": explanations or [],
                       "summary": summary}, ensure_ascii=False)

def two_findings(pack: EvidencePack) -> list[str]:
    return [item.id for item in pack.findings][:2]

def all_texts(texts) -> list[str]:
    return [
        *[t for i in texts.insights for t in (i.title, i.description)],
        *[t for r in texts.recommendations for t in (r.action, r.rationale)],
        *texts.explanations.values(),
        texts.summary,
    ]

# ---------- evidence pack ----------
def test_pack_includes_only_significant_segments_with_stable_ids():
    pack = make_pack()
    ids = [item.id for item in pack.findings]
    assert "seg:topic:bueno" in ids
    assert "seg:topic:chico" not in ids
    assert ids == [item.id for item in make_pack().findings]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z_]+:[a-z_]+:.+", i) for i in ids)

def test_pack_finding_has_formatted_numbers_and_stats_confidence():
    item = make_pack().item("seg:topic:bueno")
    assert item.category == InsightCategory.TOPIC
    assert item.numbers["posts"] == "10"
    assert re.fullmatch(r"\d+,\dx", item.numbers["mediana"])
    assert 0 < item.confidence <= 1
    assert set(item.related_post_ids) <= {f"p{i}" for i in range(10)}

def test_pack_allowed_numbers_cover_every_formatted_number():
    pack = make_pack()
    for item in [*pack.kpis, *pack.findings, *pack.best_slots]:
        assert extract_numbers(f"{item.label} {item.value}") <= pack.allowed_numbers
        assert set().union(*(extract_numbers(v) for v in item.numbers.values())) <= pack.allowed_numbers
    for post in [*pack.top_posts, *pack.bottom_posts]:
        assert extract_numbers(post.score) <= pack.allowed_numbers

def test_pack_top_and_bottom_posts():
    pack = make_pack()
    assert len(pack.top_posts) == 5
    assert len(pack.bottom_posts) == 5
    assert pack.top_posts[0].id == "p201"
    assert not {p.id for p in pack.top_posts} & {p.id for p in pack.bottom_posts}

def test_pack_prompt_json_is_valid_and_has_no_internal_fields():
    payload = json.loads(make_pack().prompt_json())
    assert "allowed_numbers" not in payload
    assert payload["findings"]

# ---------- grounding ----------
def test_extract_numbers_es_ar_formats():
    text = "Tus 40 posts de las 21 h rinden 1,4x y tienen 2,1% de engagement."
    assert extract_numbers(text) == {"40", "21 h", "1,4x", "2,1%"}

def test_extract_numbers_normalizes_variants():
    assert extract_numbers("3.386 vistas, 21hs, 1,4×, 2,1 %") == {"3386", "21 h", "1,4x", "2,1%"}
    assert extract_numbers("@user2024 y el post p30") == set()

def test_ungrounded_flags_invented_numbers():
    allowed = {"1,4x", "2,1%", "21 h", "40"}
    assert ungrounded("Rinden 3,7x tu promedio", allowed) == {"3,7x"}
    assert ungrounded("Rinden 1,4x con 2,1% a las 21 h en 40 posts", allowed) == set()

def test_ungrounded_allows_small_integers_and_bare_numbers_of_allowed_tokens():
    allowed = {"21 h", "1,4x"}
    assert ungrounded("Probá 3 veces por semana, de 1 a 7 días", allowed) == set()
    assert ungrounded("Publicá a las 21", allowed) == set()
    assert ungrounded("Hacé 12 posts", allowed) == {"12"}

# ---------- writer: grounded LLM response ----------
async def test_grounded_response_builds_contract_objects():
    pack = make_pack()
    first, second = two_findings(pack)
    raw = response_json(pack, [insight_json(pack, first, related=["p1", "ghost"]), insight_json(pack, second)])
    client = ScriptedLLMClient([raw])
    texts = await write_texts(pack, client, SETTINGS)
    assert texts.source == "llm"
    assert len(client.calls) == 1
    assert [i.id for i in texts.insights] == ["ins-1", "ins-2"]
    for insight in texts.insights:
        Insight.model_validate(insight.model_dump())
    item = pack.item(first)
    assert [(e.label, e.value) for e in texts.insights[0].evidence] == [(item.label, item.value)]
    assert texts.insights[0].confidence == item.confidence
    assert texts.insights[0].related_post_ids == ["p1"]
    assert [r.id for r in texts.recommendations] == ["rec-1", "rec-2"]
    assert texts.recommendations[0].based_on_insight_ids == ["ins-1"]
    for rec in texts.recommendations:
        Recommendation.model_validate(rec.model_dump())
    assert texts.summary

async def test_unknown_evidence_ids_are_dropped_and_insights_without_evidence_too():
    pack = make_pack()
    first, _ = two_findings(pack)
    with_ghost = insight_json(pack, first) | {"evidence_ids": [first, "seg:topic:ghost"]}
    only_ghost = insight_json(pack, first) | {"evidence_ids": ["seg:topic:ghost"]}
    client = ScriptedLLMClient([response_json(pack, [with_ghost, only_ghost, insight_json(pack, first)])])
    texts = await write_texts(pack, client, SETTINGS)
    assert len(texts.insights) == 2
    assert len(texts.insights[0].evidence) == 1

async def test_invented_number_drops_that_insight_only():
    pack = make_pack()
    first, second = two_findings(pack)
    invented = insight_json(pack, second, description="Rinde 9,7x tu post típico.")
    raw = response_json(pack, [insight_json(pack, first), invented, insight_json(pack, second)])
    client = ScriptedLLMClient([raw])
    texts = await write_texts(pack, client, SETTINGS)
    assert texts.source == "llm"
    assert len(client.calls) == 1
    assert len(texts.insights) == 2
    assert all("9,7x" not in i.description for i in texts.insights)

async def test_recommendations_follow_dropped_insights_and_priorities_renumber():
    pack = make_pack()
    first, second = two_findings(pack)
    invented = insight_json(pack, second, description="Rinde 9,7x tu post típico.")
    recs = [
        {"category": "topic", "action": "Seguí con esto.", "rationale": "Rinde.", "priority": 5, "insight_index": [0]},
        {"category": "topic", "action": "Evitá esto.", "rationale": "No rinde.", "priority": 2, "insight_index": [1]},
        {"category": "topic", "action": "Probá esto.", "rationale": "Rinde.", "priority": 9, "insight_index": [2, 7]},
    ]
    raw = response_json(pack, [insight_json(pack, first), invented, insight_json(pack, second)], recommendations=recs)
    texts = await write_texts(pack, ScriptedLLMClient([raw]), SETTINGS)
    assert [r.action for r in texts.recommendations] == ["Seguí con esto.", "Probá esto."]
    assert [r.priority for r in texts.recommendations] == [1, 2]
    assert [r.based_on_insight_ids for r in texts.recommendations] == [["ins-1"], ["ins-2"]]

async def test_mostly_invented_retries_once_then_succeeds():
    pack = make_pack()
    first, second = two_findings(pack)
    bad = [insight_json(pack, first, description=f"Rinde {n},3x.") for n in (11, 12)] + [insight_json(pack, second)]
    good = [insight_json(pack, first), insight_json(pack, second)]
    client = ScriptedLLMClient([response_json(pack, bad), response_json(pack, good)])
    texts = await write_texts(pack, client, SETTINGS)
    assert len(client.calls) == 2
    assert "11,3x" in client.calls[1].user
    assert texts.source == "llm"
    assert len(texts.insights) == 2

async def test_mostly_invented_twice_falls_back_to_templates():
    pack = make_pack()
    first, second = two_findings(pack)
    bad = [insight_json(pack, first, description=f"Rinde {n},3x.") for n in (11, 12)] + [insight_json(pack, second)]
    client = ScriptedLLMClient([response_json(pack, bad), response_json(pack, bad)])
    texts = await write_texts(pack, client, SETTINGS)
    assert len(client.calls) == 2
    assert texts.source == "template"
    assert texts.errors

async def test_llm_exception_falls_back_to_templates_without_raising():
    pack = make_pack()
    texts = await write_texts(pack, ScriptedLLMClient([LLMError("down")]), SETTINGS)
    assert texts.source == "template"
    assert texts.errors
    assert texts.insights == template_texts(pack).insights
    assert 1 <= len(texts.insights) <= min(len(pack.findings), MAX_INSIGHTS)

async def test_llm_disabled_or_no_client_uses_templates_with_zero_calls():
    pack = make_pack()
    client = ScriptedLLMClient([])
    texts = await write_texts(pack, client, replace(SETTINGS, enable_llm=False))
    assert client.calls == []
    assert texts.source == "template"
    assert (await write_texts(pack, None, SETTINGS)).source == "template"

async def test_explanations_cover_top_and_bottom_posts_and_ungrounded_ones_are_replaced():
    pack = make_pack()
    first, _ = two_findings(pack)
    top = pack.top_posts[0]
    bottom = pack.bottom_posts[0]
    explanations = [
        {"post_id": top.id, "text": f"Rindió {top.score} tu post típico por el tema."},
        {"post_id": bottom.id, "text": "Rindió 0,01x, malísimo."},
        {"post_id": "ghost", "text": "No existe."},
    ]
    raw = response_json(pack, [insight_json(pack, first)], explanations=explanations)
    texts = await write_texts(pack, ScriptedLLMClient([raw]), SETTINGS)
    expected = {p.id for p in [*pack.top_posts, *pack.bottom_posts]}
    assert set(texts.explanations) == expected
    assert texts.explanations[top.id] == f"Rindió {top.score} tu post típico por el tema."
    assert "0,01x" not in texts.explanations[bottom.id]

async def test_ungrounded_or_empty_summary_is_replaced():
    pack = make_pack()
    first, _ = two_findings(pack)
    raw = response_json(pack, [insight_json(pack, first)], summary="Creciste 87,5% este mes.")
    texts = await write_texts(pack, ScriptedLLMClient([raw]), SETTINGS)
    assert "87,5%" not in texts.summary
    assert texts.summary

async def test_writer_uses_the_writer_model_and_a_stable_system_prompt():
    pack = make_pack()
    first, _ = two_findings(pack)
    client = ScriptedLLMClient([response_json(pack, [insight_json(pack, first)])])
    await write_texts(pack, client, replace(SETTINGS, writer_model="x/writer"))
    call: LLMCall = client.calls[0]
    assert call.model == "x/writer"
    assert call.system == WRITER_SYSTEM
    assert issubclass(call.schema, WriterResponse)
    assert not re.search(r"\b20\d\d\b", WRITER_SYSTEM)
    assert not re.search(r"\b\d{1,2}:\d{2}\b", WRITER_SYSTEM)

async def test_extra_insights_are_capped_instead_of_failing():
    pack = make_pack()
    first, _ = two_findings(pack)
    raw = response_json(pack, [insight_json(pack, first)] * (MAX_INSIGHTS + 2))
    texts = await write_texts(pack, ScriptedLLMClient([raw]), SETTINGS)
    assert texts.source == "llm"
    assert len(texts.insights) == MAX_INSIGHTS
    assert len(texts.recommendations) <= MAX_INSIGHTS

# ---------- templates ----------
def test_template_texts_are_grounded_and_valid():
    pack = make_pack()
    texts = template_texts(pack)
    assert texts.source == "template"
    assert 1 <= len(texts.insights) <= min(len(pack.findings), MAX_INSIGHTS)
    assert texts.recommendations
    assert set(texts.explanations) == {p.id for p in [*pack.top_posts, *pack.bottom_posts]}
    for text in all_texts(texts):
        assert text
        assert ungrounded(text, pack.allowed_numbers) == set(), text
    for insight in texts.insights:
        Insight.model_validate(insight.model_dump())

def test_template_insights_do_not_repeat_a_dimension_and_direction():
    pack = fixture_pack()
    texts = template_texts(pack)
    keys = []
    for insight in texts.insights:
        shown = (insight.evidence[0].label, insight.evidence[0].value)
        item = next(i for i in pack.findings if (i.label, i.value) == shown)
        family = "timing" if item.kind == "timing" else item.id.split(":")[1]
        keys.append((family, item.direction))
    assert len(keys) == len(set(keys))

def test_template_on_fixture_leads_with_presupuesto():
    pack = fixture_pack()
    texts = template_texts(pack)
    assert any("presupuesto" in i.title for i in texts.insights)
    assert all(ungrounded(t, pack.allowed_numbers) == set() for t in all_texts(texts))
    assert texts.summary.startswith("Analizamos 40 posts de @")
