"""
Stage 11 (AI): the creator brief ("el para qué") frames labeling, insights, drafts and the sandbox, never the
numbers. Without a brief everything behaves as before. All LLM calls are scripted.
"""
import json
import re
from datetime import UTC, datetime, timedelta
from eduhub_ai.analyzer import HybridAnalyzer
from eduhub_ai.config import load_settings
from eduhub_ai.context import brief_payload, mentions_avoided
from eduhub_ai.features import extract_deterministic
from eduhub_ai.generation.generator import LLMDraftGenerator
from eduhub_ai.insights import build_evidence, template_texts, write_texts
from eduhub_ai.insights.evidence import brief_numbers
from eduhub_ai.insights.grounding import ungrounded
from eduhub_ai.insights.writer import WriterResponse
from eduhub_ai.labeling.labeler import build_taxonomy
from eduhub_ai.labeling.schemas import LabelBatchResponse, TaxonomyResponse
from eduhub_ai.llm.client import LLMCall
from eduhub_ai.llm.scripted import ScriptedLLMClient
from eduhub_ai.sandbox.simulator import LLMAudienceSimulator
from eduhub_ai.stats import best_time_slots, build_heatmap, build_kpis
from eduhub_shared.fixtures import load_report, load_snapshot
from eduhub_shared.metrics import compute_rates
from eduhub_shared.models import (
    AccountProfile,
    AnalyzedPost,
    AudienceFilters,
    CreatorContext,
    DraftRequest,
    Post,
    PostMetrics,
    SimulationRequest,
)
from eduhub_shared.testing import check_analyzer, check_generator, check_simulator

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
SETTINGS = load_settings({})
PROFILE = AccountProfile(handle="demo", display_name="Demo", followers_count=1000, following_count=10, posts_count=50)
BRIEF = CreatorContext(
    goal="sell", goal_detail="Queremos 500 ventas este mes", offering="Ebook 'Soy Solito'",
    target_audience="Gente que vive sola", audience_filters=AudienceFilters(age_groups=["18 a 29 años"]),
    brand_voice="Cercana y con humor", avoid_topics=["Política"], preferred_cta="link",
)
POST_LINE = re.compile(r'^\{"id": .*\}$', re.MULTILINE)

def user_json(call: LLMCall) -> dict:
    return json.loads(call.user.split("\n", 1)[1].split("\n\n")[0])

class PipelineLLM:
    """
    Answers taxonomy, label batches and the writer (with no insights, so templates are used).
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

def make_post(i: int) -> Post:
    return Post(id=f"p{i}", author_handle="demo", text=f"Post {i}", created_at=NOW - timedelta(days=3, hours=7 * i),
                url=f"https://x.com/demo/status/{i}",
                metrics=PostMetrics(impressions=1000, likes=20, reposts=0, quotes=0, replies=0, bookmarks=0))

def analyzed(i: int, score: float, **labels: str) -> AnalyzedPost:
    post = make_post(i)
    features = extract_deterministic(post, []).model_copy(update=labels)
    return AnalyzedPost(post=post, features=features, rates=compute_rates(post.metrics), score=score)

def link_posts() -> list[AnalyzedPost]:
    posts = [analyzed(i, 0.4 + 0.02 * i, cta="link", topic="cocina") for i in range(10)]
    return posts + [analyzed(100 + i, 1.5 + 0.02 * i, cta="ninguno", topic="cocina") for i in range(10)]

def politics_posts() -> list[AnalyzedPost]:
    posts = [analyzed(i, 2.0 + 0.02 * i, topic="política") for i in range(10)]
    return posts + [analyzed(100 + i, 0.8 + 0.02 * i, topic="cocina") for i in range(10)]

def pack_for(posts: list[AnalyzedPost], context: CreatorContext | None):
    kpis = build_kpis([p.post for p in posts])
    return build_evidence(PROFILE, kpis, posts, best_time_slots(build_heatmap(posts)), context=context)

def all_texts(texts) -> list[str]:
    return [*[t for i in texts.insights for t in (i.title, i.description)],
            *[t for r in texts.recommendations for t in (r.action, r.rationale)],
            *texts.explanations.values(), texts.summary]

# ---------- brief helpers ----------
def test_brief_payload_is_none_without_content():
    assert brief_payload(None) is None
    assert brief_payload(CreatorContext()) is None

def test_brief_payload_has_es_ar_keys_and_no_empty_fields():
    payload = brief_payload(BRIEF)
    assert payload["objetivo"] == "vender un producto o servicio"
    assert payload["oferta"] == "Ebook 'Soy Solito'"
    assert payload["temas_a_evitar"] == ["Política"]
    assert payload["cta_preferido"] == "link"
    assert payload["audiencia_objetivo"]["edades"] == ["18 a 29 años"]
    partial = brief_payload(CreatorContext(offering="Curso"))
    assert partial == {"oferta": "Curso"}

def test_brief_numbers_and_avoided_topics():
    assert "500" in brief_numbers(BRIEF)
    assert brief_numbers(None) == set()
    assert mentions_avoided("Hoy hablo de politica y precios", BRIEF)
    assert not mentions_avoided("Políticas de devolución de la tienda", BRIEF)
    assert not mentions_avoided("Receta de flan", None)

# ---------- analyzer ----------
async def test_report_echoes_the_brief_with_and_without_one():
    snapshot = load_snapshot()
    analyzer = HybridAnalyzer(SETTINGS, None, clock=lambda: NOW)
    with_brief = await check_analyzer(analyzer, snapshot.model_copy(update={"context": BRIEF}))
    assert with_brief.context == BRIEF
    without = await check_analyzer(analyzer, snapshot.model_copy(update={"context": None}))
    assert without.context is None

async def test_no_brief_and_empty_brief_send_the_same_prompts_and_give_the_same_report():
    snapshot = load_snapshot()
    runs = []
    for context in (None, CreatorContext()):
        llm = PipelineLLM()
        analyzer = HybridAnalyzer(SETTINGS, ScriptedLLMClient([llm] * 40), clock=lambda: NOW)
        report = await analyzer.analyze(snapshot.model_copy(update={"context": context}))
        runs.append((llm.calls, report))
    (calls_a, report_a), (calls_b, report_b) = runs
    assert [c.user for c in calls_a] == [c.user for c in calls_b]
    assert all("contexto_del_creador" not in c.user and "Contexto del creador" not in c.user for c in calls_a)
    assert report_a.model_dump(exclude={"context"}) == report_b.model_dump(exclude={"context"})

# ---------- labeling ----------
async def test_taxonomy_prompt_gets_the_offering_as_a_hint():
    llm = PipelineLLM()
    posts = load_snapshot().posts
    await build_taxonomy(posts, ScriptedLLMClient([llm]), SETTINGS, context=BRIEF)
    assert "Ebook 'Soy Solito'" in llm.calls[0].user
    llm_plain = PipelineLLM()
    await build_taxonomy(posts, ScriptedLLMClient([llm_plain]), SETTINGS)
    assert "Soy Solito" not in llm_plain.calls[0].user

# ---------- writer ----------
async def test_writer_sees_the_brief_and_brief_numbers_are_grounded():
    pack = pack_for(link_posts(), BRIEF)
    assert "contexto_del_creador" in pack.prompt_json()
    assert "contexto_del_creador" not in pack_for(link_posts(), None).prompt_json()
    finding = pack.findings[0]
    insight = {"category": finding.category.value, "title": "Para tus 500 ventas", "description": "Enfocate en esto.",
               "evidence_ids": [finding.id], "impact": "high", "related_post_ids": []}
    invented = dict(insight, title="Vas a vender 700 ebooks")
    raw = json.dumps({"insights": [insight, invented, insight], "recommendations": [], "explanations": [],
                      "summary": "Resumen."})
    client = ScriptedLLMClient([raw])
    texts = await write_texts(pack, client, SETTINGS)
    assert issubclass(client.calls[0].schema, WriterResponse)
    assert "contexto_del_creador" in client.calls[0].user
    assert [i.title for i in texts.insights] == ["Para tus 500 ventas", "Para tus 500 ventas"]

# ---------- templates ----------
def test_selling_goal_turns_the_link_finding_into_a_trade_off():
    with_brief = template_texts(pack_for(link_posts(), BRIEF))
    plain = template_texts(pack_for(link_posts(), None))
    trade_off = [r.action for r in with_brief.recommendations if "respuesta o en tu bio" in r.action]
    assert trade_off
    assert not any("respuesta o en tu bio" in r.action for r in plain.recommendations)
    assert any("link" in r.action and r.action.startswith("Publicá menos") for r in plain.recommendations)
    pack = pack_for(link_posts(), BRIEF)
    assert all(ungrounded(t, pack.allowed_numbers) == set() for t in all_texts(with_brief))
    assert "Tu objetivo: vender un producto o servicio." in with_brief.summary
    assert "Tu objetivo" not in plain.summary

def test_avoided_topics_get_no_template_insight():
    plain = template_texts(pack_for(politics_posts(), None))
    assert any("política" in i.title for i in plain.insights)
    filtered = template_texts(pack_for(politics_posts(), BRIEF))
    assert not any("política" in t.casefold() for i in filtered.insights for t in (i.title, i.description))

# ---------- generator ----------
class DraftLLM:
    def __init__(self, texts: list[str] | None = None) -> None:
        self.texts = texts
        self.calls: list[LLMCall] = []

    def __call__(self, call: LLMCall) -> str:
        self.calls.append(call)
        count = user_json(call)["cantidad"]
        texts = self.texts if self.texts is not None else [f"Borrador {len(self.calls)}.{i}" for i in range(count)]
        drafts = [{"text": t, "rationale": "Vende el producto.", "topic": "presupuesto", "tone": "informativo",
                   "hook": "pregunta", "cta": "link", "media": "video"} for t in texts]
        return json.dumps({"drafts": drafts}, ensure_ascii=False)

def generator(*responders) -> LLMDraftGenerator:
    return LLMDraftGenerator(SETTINGS, ScriptedLLMClient(list(responders) or [DraftLLM()] * 4), clock=lambda: NOW)

async def test_generator_uses_the_request_brief_over_the_report_brief():
    report = load_report()
    assert report.context is not None
    llm = DraftLLM()
    await generator(llm).generate(DraftRequest(handle="demo_finanzas", context=BRIEF), report, [])
    assert user_json(llm.calls[0])["brief"]["oferta"] == "Ebook 'Soy Solito'"
    from_report = DraftLLM()
    await generator(from_report).generate(DraftRequest(handle="demo_finanzas"), report, [])
    assert user_json(from_report.calls[0])["brief"]["oferta"] == report.context.offering
    none = DraftLLM()
    plain_report = report.model_copy(update={"context": None})
    await generator(none).generate(DraftRequest(handle="demo_finanzas"), plain_report, [])
    assert "brief" not in user_json(none.calls[0])

async def test_preferred_cta_replaces_the_best_ctas():
    llm = DraftLLM()
    await generator(llm).generate(DraftRequest(handle="demo_finanzas", context=BRIEF), load_report(), [])
    assert user_json(llm.calls[0])["mejores_cta"] == ["link"]

async def test_drafts_about_avoided_topics_are_dropped_and_refilled():
    first = DraftLLM(texts=["Opinión sobre política y ahorro", "Ahorrá el día que cobrás", "Tu planilla gratis"])
    second = DraftLLM()
    drafts = await generator(first, second).generate(DraftRequest(handle="demo_finanzas", context=BRIEF),
                                                     load_report(), [])
    assert len(drafts) == 3
    assert not any(mentions_avoided(d.text, BRIEF) for d in drafts)
    assert user_json(second.calls[0])["cantidad"] == 1

async def test_generator_contract_still_holds_with_a_brief_in_the_report():
    await check_generator(generator(*[DraftLLM()] * 4))

# ---------- simulator ----------
class AudienceLLM:
    def __init__(self) -> None:
        self.calls: list[LLMCall] = []

    def __call__(self, call: LLMCall) -> str:
        self.calls.append(call)
        payload = user_json(call)
        return json.dumps({"reactions": [
            {"persona_id": p["id"], "variant_index": v["indice"], "reaction": "read", "comment": None, "sentiment": 0.0}
            for p in payload["personas"] for v in payload["variantes"]]})

def simulator(llm: AudienceLLM) -> LLMAudienceSimulator:
    return LLMAudienceSimulator(SETTINGS, ScriptedLLMClient([llm] * 30), clock=lambda: NOW)

async def test_simulator_uses_the_brief_audience_when_no_filters_are_given():
    llm = AudienceLLM()
    result = await simulator(llm).simulate(SimulationRequest(variants=["a", "b"], audience_size=20, context=BRIEF))
    assert all(p.age_group == "18 a 29 años" for p in result.personas)
    assert user_json(llm.calls[0])["producto"] == "Ebook 'Soy Solito'"
    assert "audiencia objetivo de tu brief" in result.summary

async def test_explicit_filters_win_over_the_brief():
    llm = AudienceLLM()
    request = SimulationRequest(variants=["a", "b"], audience_size=20, context=BRIEF,
                                filters=AudienceFilters(genders=["Varón"]))
    result = await simulator(llm).simulate(request)
    assert all(p.gender == "Varón" for p in result.personas)
    assert {p.age_group for p in result.personas} != {"18 a 29 años"}
    assert "audiencia objetivo de tu brief" not in result.summary

async def test_simulator_without_a_brief_is_unchanged_and_contract_holds():
    llm = AudienceLLM()
    await check_simulator(simulator(llm))
    assert "producto" not in user_json(llm.calls[0])
