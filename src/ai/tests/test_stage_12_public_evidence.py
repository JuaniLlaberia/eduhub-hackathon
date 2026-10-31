"""
Stage 12: public evidence (OpenARG facts) in the insights. Facts are a packaged catalog (no network); an insight
may cite at most one, always next to account evidence. Without public facts everything behaves as before.
All LLM calls are scripted.
"""
import json
import re
from datetime import UTC, datetime, timedelta
from eduhub_ai.analyzer import HybridAnalyzer
from eduhub_ai.config import load_settings
from eduhub_ai.features import extract_deterministic
from eduhub_ai.insights import build_evidence, write_texts
from eduhub_ai.insights.grounding import extract_numbers
from eduhub_ai.insights.prompts import WRITER_SYSTEM
from eduhub_ai.insights.writer import WriterResponse
from eduhub_ai.labeling.schemas import LabelBatchResponse, TaxonomyResponse
from eduhub_ai.llm.client import LLMCall
from eduhub_ai.llm.scripted import ScriptedLLMClient
from eduhub_ai.public_data import (
    MAX_PUBLIC_FACTS,
    PUBLIC_LABEL_PREFIX,
    load_public_facts,
    select_public_facts,
)
from eduhub_ai.sandbox.personas import load_personas
from eduhub_ai.stats import best_time_slots, build_heatmap, build_kpis
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.metrics import compute_rates
from eduhub_shared.models import AccountProfile, AnalyzedPost, AudienceFilters, CreatorContext, Post, PostMetrics
from eduhub_shared.testing import check_analyzer

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
SETTINGS = load_settings({})
PROFILE = AccountProfile(handle="demo", display_name="Demo", followers_count=1000, following_count=10, posts_count=50)
YOUNG = CreatorContext(audience_filters=AudienceFilters(age_groups=["18 a 29 años"]))
POST_LINE = re.compile(r'^\{"id": .*\}$', re.MULTILINE)
ES_AR_NUMBER = re.compile(r"\d+\.\d(?!\d)")

def make_post(i: int) -> Post:
    return Post(id=f"p{i}", author_handle="demo", text=f"Post {i}", created_at=NOW - timedelta(days=3, hours=7 * i),
                url=f"https://x.com/demo/status/{i}",
                metrics=PostMetrics(impressions=1000, likes=20, reposts=0, quotes=0, replies=0, bookmarks=0))

def analyzed(i: int, score: float, topic: str) -> AnalyzedPost:
    post = make_post(i)
    features = extract_deterministic(post, []).model_copy(update={"topic": topic})
    return AnalyzedPost(post=post, features=features, rates=compute_rates(post.metrics), score=score)

def synthetic_posts() -> list[AnalyzedPost]:
    posts = [analyzed(i, 2.0 + 0.02 * i, "bueno") for i in range(10)]
    return posts + [analyzed(100 + i, 0.8 + 0.04 * i, "normal") for i in range(10)]

def make_pack(context: CreatorContext | None = None, with_public: bool = True):
    posts = synthetic_posts()
    kpis = build_kpis([p.post for p in posts])
    public = select_public_facts(context) if with_public else None
    return build_evidence(PROFILE, kpis, posts, best_time_slots(build_heatmap(posts)), public_facts=public)

def insight(evidence_ids: list[str], description: str = "Tus posts sobre bueno rinden más.") -> dict:
    return {"category": "topic", "title": "Lo bueno rinde", "description": description,
            "evidence_ids": evidence_ids, "impact": "high", "related_post_ids": []}

def response(insights: list[dict]) -> str:
    return json.dumps({"insights": insights, "recommendations": [], "explanations": [], "summary": ""})

def account_id(pack) -> str:
    return pack.findings[0].id

class PipelineLLM:
    """
    Answers taxonomy, label batches and the writer (no insights, so templates fill in); records every call.
    """
    def __init__(self) -> None:
        self.calls: list[LLMCall] = []

    def __call__(self, call: LLMCall) -> str:
        self.calls.append(call)
        if call.schema is TaxonomyResponse:
            return json.dumps({"topics": ["presupuesto", "ahorro", "sueldo", "inversiones", "tarjetas"]})
        if issubclass(call.schema, LabelBatchResponse):
            ids = [json.loads(line)["id"] for line in POST_LINE.findall(call.user)]
            return json.dumps({"labels": [{"post_id": i, "topic": "otros", "tone": "informativo", "sentiment": 0.0,
                                           "hook": "dato", "cta": "ninguno"} for i in ids]})
        return json.dumps({"insights": [], "recommendations": [], "explanations": [], "summary": ""})

    def writer_calls(self) -> list[LLMCall]:
        return [c for c in self.calls if issubclass(c.schema, WriterResponse)]

# ---------- catalog ----------
def test_catalog_facts_are_complete_and_sourced():
    facts = load_public_facts()
    assert len(facts) >= 5
    assert len({f.id for f in facts}) == len(facts)
    for fact in facts:
        assert fact.source and fact.text
        assert fact.url.startswith("https://")
        assert extract_numbers(fact.text), fact.id
        assert not ES_AR_NUMBER.search(fact.text), f"{fact.id}: use a decimal comma"

def test_catalog_age_groups_match_the_persona_values():
    known = {p.age_group for p in load_personas()}
    used = {group for fact in load_public_facts() for group in fact.age_groups}
    assert used and used <= known

def test_selection_without_brief_offers_only_general_facts():
    items = select_public_facts(None)
    general = [f for f in load_public_facts() if not f.age_groups]
    assert 0 < len(items) <= MAX_PUBLIC_FACTS
    assert {i.id for i in items} <= {f"pub:{f.id}" for f in general}
    assert select_public_facts(CreatorContext()) == items
    for item in items:
        assert item.kind == "public"
        assert item.id.startswith("pub:")
        assert item.label.startswith(PUBLIC_LABEL_PREFIX)
        assert item.confidence is None and item.related_post_ids == []

def test_selection_puts_the_brief_age_group_first_and_skips_other_ages():
    facts = {f"pub:{f.id}": f for f in load_public_facts()}
    items = select_public_facts(YOUNG)
    assert len(items) <= MAX_PUBLIC_FACTS
    assert facts[items[0].id].age_groups == ["18 a 29 años"]
    for item in items:
        assert facts[item.id].age_groups in ([], ["18 a 29 años"])

# ---------- evidence pack ----------
def test_pack_without_public_facts_is_unchanged():
    plain = make_pack(with_public=False)
    assert plain.public_facts == []
    assert "datos_publicos" not in json.loads(plain.prompt_json())
    posts = synthetic_posts()
    kpis = build_kpis([p.post for p in posts])
    empty = build_evidence(PROFILE, kpis, posts, best_time_slots(build_heatmap(posts)), public_facts=[])
    assert empty.prompt_json() == plain.prompt_json()
    assert empty.allowed_numbers == plain.allowed_numbers

def test_pack_offers_public_facts_to_the_writer_and_allows_their_numbers():
    pack = make_pack()
    payload = json.loads(pack.prompt_json())
    assert [p["id"] for p in payload["datos_publicos"]] == [i.id for i in pack.public_facts]
    assert all(set(p) == {"id", "label", "value"} for p in payload["datos_publicos"])
    for item in pack.public_facts:
        assert pack.item(item.id) == item
        assert extract_numbers(item.value) <= pack.allowed_numbers

# ---------- writer ----------
async def test_insight_can_cite_one_public_fact_after_its_account_evidence():
    pack = make_pack()
    public = pack.public_facts[0]
    raw = response([insight([public.id, account_id(pack)])])
    texts = await write_texts(pack, ScriptedLLMClient([raw]), SETTINGS)
    [only] = texts.insights
    labels = [e.label for e in only.evidence]
    assert labels == [pack.findings[0].label, public.label]
    alone = await write_texts(pack, ScriptedLLMClient([response([insight([account_id(pack)])])]), SETTINGS)
    assert only.confidence == alone.insights[0].confidence
    assert only.related_post_ids == alone.insights[0].related_post_ids

async def test_public_only_insights_are_dropped():
    pack = make_pack()
    raw = response([insight([account_id(pack)]), insight([pack.public_facts[0].id])])
    texts = await write_texts(pack, ScriptedLLMClient([raw]), SETTINGS)
    assert len(texts.insights) == 1
    assert all(any(not e.label.startswith(PUBLIC_LABEL_PREFIX) for e in i.evidence) for i in texts.insights)

async def test_at_most_one_public_fact_per_insight():
    pack = make_pack()
    ids = [account_id(pack), *(i.id for i in pack.public_facts[:2])]
    texts = await write_texts(pack, ScriptedLLMClient([response([insight(ids)])]), SETTINGS)
    public = [e for e in texts.insights[0].evidence if e.label.startswith(PUBLIC_LABEL_PREFIX)]
    assert len(public) == 1

async def test_a_public_number_quoted_in_the_text_is_grounded():
    pack = make_pack()
    fact = pack.public_facts[0]
    number = sorted(extract_numbers(fact.value))[0]
    raw = response([insight([account_id(pack), fact.id], f"Tus posts sobre bueno rinden más; dato: {number}.")])
    texts = await write_texts(pack, ScriptedLLMClient([raw]), SETTINGS)
    assert number in texts.insights[0].description

def test_writer_prompt_explains_public_facts():
    assert "datos_publicos" in WRITER_SYSTEM
    assert not re.search(r"\b20\d\d\b", WRITER_SYSTEM)

# ---------- settings and analyzer ----------
def test_public_evidence_setting_defaults_on_and_can_be_turned_off():
    assert load_settings({}).enable_public_evidence is True
    assert load_settings({"AI_PUBLIC_EVIDENCE": "0"}).enable_public_evidence is False
    assert load_settings({"AI_PUBLIC_EVIDENCE": "1"}).enable_public_evidence is True

async def test_analyzer_offers_public_facts_unless_turned_off():
    snapshot = load_snapshot()
    prompts = {}
    for flag in ("1", "0"):
        llm = PipelineLLM()
        analyzer = HybridAnalyzer(load_settings({"AI_PUBLIC_EVIDENCE": flag}), ScriptedLLMClient([llm] * 40),
                                  clock=lambda: NOW)
        await check_analyzer(analyzer, snapshot)
        prompts[flag] = llm.writer_calls()[0].user
    assert "datos_publicos" in prompts["1"]
    assert "datos_publicos" not in prompts["0"]

async def test_template_mode_report_has_no_public_evidence():
    report = await check_analyzer(HybridAnalyzer(SETTINGS, None, clock=lambda: NOW), load_snapshot())
    assert all(not e.label.startswith(PUBLIC_LABEL_PREFIX) for i in report.insights for e in i.evidence)
