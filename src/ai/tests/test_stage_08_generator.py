"""
Stage 08: LLM draft generator in the creator's voice, with suggested times on the best slots and estimated
scores from the account's own pattern model (or segment stats). All LLM calls are scripted.
"""
import json
import re
from dataclasses import replace
from datetime import UTC, datetime
from zoneinfo import ZoneInfo
import pytest
from eduhub_ai import create_generator
from eduhub_ai.config import load_settings
from eduhub_ai.generation.generator import LLMDraftGenerator
from eduhub_ai.generation.prompts import GENERATOR_SYSTEM
from eduhub_ai.generation.schemas import DraftsResponse
from eduhub_ai.llm.client import LLMCall, LLMError
from eduhub_ai.llm.scripted import ScriptedLLMClient
from eduhub_shared.errors import GenerationError, RateLimitedError
from eduhub_shared.fakes import FakeDraftGenerator
from eduhub_shared.fixtures import load_report, load_snapshot
from eduhub_shared.interfaces import DraftGenerator
from eduhub_shared.models import AnalysisReport, DraftRequest, MediaType, SegmentDimension, SegmentStat
from eduhub_shared.testing import check_generator

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
AR_TZ = ZoneInfo("America/Argentina/Buenos_Aires")
SETTINGS = load_settings({})
AI_ENV = ("OPENROUTER_API_KEY", "AI_ENABLE_LLM")

def draft_item(text: str, topic: str = "presupuesto") -> dict:
    return {"text": text, "rationale": "Usa tu tema más fuerte.", "topic": topic, "tone": "informativo",
            "hook": "pregunta", "cta": "guardar", "media": "video"}

def payload_of(call: LLMCall) -> dict:
    return json.loads(call.user.split("\n", 1)[1].split("\n\n")[0])

class Responder:
    """
    Answers with as many distinct drafts as the request asks for (or a fixed list of texts).
    """
    def __init__(self, texts: list[str] | None = None) -> None:
        self.texts = texts
        self.calls: list[LLMCall] = []

    def __call__(self, call: LLMCall) -> str:
        self.calls.append(call)
        count = payload_of(call)["cantidad"]
        texts = self.texts if self.texts is not None else [
            f"¿Armaste tu presupuesto de noviembre? Idea {len(self.calls)}.{i} 💸" for i in range(count)]
        return json.dumps({"drafts": [draft_item(t) for t in texts]}, ensure_ascii=False)

def generator(client: ScriptedLLMClient, scorer=None) -> LLMDraftGenerator:
    return LLMDraftGenerator(SETTINGS, client, clock=lambda: NOW, scorer=scorer)

def scripted(*responders) -> ScriptedLLMClient:
    return ScriptedLLMClient(list(responders) or [Responder()] * 4)

def request(**fields) -> DraftRequest:
    report = load_report()
    return DraftRequest(handle=report.profile.handle, **fields)

async def generate(gen: LLMDraftGenerator, report: AnalysisReport | None = None, **fields):
    return await gen.generate(request(**fields), report or load_report(), load_snapshot().trends)

# ---------- contract ----------
async def test_contract_with_scripted_llm():
    drafts = await check_generator(generator(scripted()))
    assert all(d.rationale for d in drafts)
    assert all(d.suggested_time is not None for d in drafts)

# ---------- prompt ----------
async def test_prompt_has_voice_examples_recommendation_and_at_most_three_trends():
    report = load_report()
    responder = Responder()
    rec = report.recommendations[1]
    await generate(generator(scripted(responder)), report, recommendation_id=rec.id)
    payload = payload_of(responder.calls[0])
    top = sorted((p for p in report.posts if p.score is not None), key=lambda p: (-(p.score or 0), p.post.id))
    for item in top[:5]:
        assert item.post.text in payload["ejemplos"]
    assert rec.action in json.dumps(payload["objetivo"], ensure_ascii=False)
    assert len(load_snapshot().trends) > 3
    assert len(payload["tendencias"]) == 3
    assert payload["cantidad"] == 3

async def test_prompt_uses_requested_topic_and_instructions():
    responder = Responder()
    await generate(generator(scripted(responder)), topic="aguinaldo", instructions="Que sea un hilo corto.")
    payload = payload_of(responder.calls[0])
    assert payload["tema"] == "aguinaldo"
    assert payload["instrucciones"] == "Que sea un hilo corto."

async def test_system_prompt_is_stable_and_uses_writer_settings():
    responder = Responder()
    settings = replace(SETTINGS, writer_model="x/writer", writer_reasoning="minimal")
    gen = LLMDraftGenerator(settings, scripted(responder), clock=lambda: NOW)
    await generate(gen)
    call = responder.calls[0]
    assert (call.model, call.reasoning, call.system) == ("x/writer", "minimal", GENERATOR_SYSTEM)
    assert issubclass(call.schema, DraftsResponse)
    assert not re.search(r"\b20\d\d\b", GENERATOR_SYSTEM)

async def test_default_topic_needs_at_least_three_posts():
    report = load_report()
    lucky = SegmentStat(dimension=SegmentDimension.TOPIC, value="suerte", post_count=1, avg_score=9.0,
                        engagement_rate=0.1)
    tweaked = report.model_copy(update={"segments": [lucky, *report.segments]})
    responder = Responder()
    await generate(generator(scripted(responder)), tweaked)
    payload = payload_of(responder.calls[0])
    assert payload["tema"] == "presupuesto"
    assert "suerte" in payload["temas_de_la_cuenta"]

# ---------- count, retry, dedupe ----------
async def test_fewer_drafts_trigger_one_retry_for_the_missing_ones():
    first = Responder(texts=["Uno sobre presupuesto"])
    second = Responder()
    drafts = await generate(generator(scripted(first, second)))
    assert len(drafts) == 3
    assert payload_of(second.calls[0])["cantidad"] == 2
    assert "Uno sobre presupuesto" in second.calls[0].user

async def test_still_too_few_after_retry_raises_generation_error():
    one = Responder(texts=["Uno sobre presupuesto"])
    with pytest.raises(GenerationError) as info:
        await generate(generator(scripted(one, one)))
    assert info.value.message

async def test_duplicates_and_empty_texts_are_removed():
    first = Responder(texts=["Ahorrá  primero", "ahorrá primero", "   ", "Otro tema distinto"])
    second = Responder()
    drafts = await generate(generator(scripted(first, second)))
    texts = [d.text for d in drafts]
    assert len(texts) == 3
    assert texts[:2] == ["Ahorrá  primero", "Otro tema distinto"]
    assert len({t.casefold() for t in texts}) == 3

async def test_extra_drafts_are_trimmed_to_count_with_unique_ids():
    many = Responder(texts=[f"Idea número {i}" for i in range(6)])
    drafts = await generate(generator(scripted(many)), count=2)
    assert [d.text for d in drafts] == ["Idea número 0", "Idea número 1"]
    assert len({d.id for d in drafts}) == 2

# ---------- suggested time ----------
async def test_suggested_times_are_future_best_slots_in_argentina_time():
    report = load_report()
    drafts = await generate(generator(scripted()), report)
    best = [(s.weekday, s.hour) for s in report.best_time_slots]
    for draft in drafts:
        local = draft.suggested_time.astimezone(AR_TZ)
        assert draft.suggested_time > NOW
        assert (local.weekday(), local.hour) in best
    first = drafts[0].suggested_time.astimezone(AR_TZ)
    assert (first.weekday(), first.hour) == best[0]

# ---------- estimated score ----------
async def test_injected_scorer_is_used():
    seen = []

    def scorer(features):
        seen.append(features)
        return 1.7

    drafts = await generate(generator(scripted(), scorer=scorer))
    assert [d.estimated_score for d in drafts] == [1.7, 1.7, 1.7]
    assert seen[0].topic == "presupuesto"
    assert seen[0].hook == "pregunta"
    assert seen[0].media_type == MediaType.VIDEO

async def test_default_scorer_uses_the_pattern_model_when_it_can():
    drafts = await generate(generator(scripted()))
    assert all(d.estimated_score is not None and d.estimated_score > 0 for d in drafts)

async def test_default_scorer_falls_back_to_the_topic_segment():
    report = load_report()
    small = report.model_copy(update={"posts": report.posts[:10]})
    topic = next(s for s in report.segments if s.dimension == SegmentDimension.TOPIC and s.value == "presupuesto")
    drafts = await generate(generator(scripted()), small)
    assert all(d.estimated_score == topic.avg_score for d in drafts)
    unknown = Responder(texts=["a", "b", "c"])
    unknown_drafts = await LLMDraftGenerator(SETTINGS, scripted(unknown), clock=lambda: NOW).generate(
        request(), small, [])
    assert all(d.estimated_score is not None for d in unknown_drafts)

async def test_unknown_topic_and_no_model_gives_no_score():
    report = load_report()
    small = report.model_copy(update={"posts": report.posts[:10]})

    def other_topic(call: LLMCall) -> str:
        count = payload_of(call)["cantidad"]
        return json.dumps({"drafts": [draft_item(f"Texto {i}", topic="otros") for i in range(count)]})

    drafts = await generate(generator(ScriptedLLMClient([other_topic])), small)
    assert all(d.estimated_score is None for d in drafts)

# ---------- insights ----------
async def test_based_on_the_selected_recommendation_or_top_insights():
    report = load_report()
    rec = report.recommendations[0]
    drafts = await generate(generator(scripted()), report, recommendation_id=rec.id)
    assert all(d.based_on_insight_ids == rec.based_on_insight_ids for d in drafts)
    default = await generate(generator(scripted()), report, recommendation_id="ghost")
    known = {i.id for i in report.insights}
    assert all(d.based_on_insight_ids and set(d.based_on_insight_ids) <= known for d in default)

# ---------- errors ----------
async def test_llm_failure_raises_generation_error_in_spanish():
    with pytest.raises(GenerationError) as info:
        await generate(generator(ScriptedLLMClient([LLMError("down")])))
    assert "borradores" in info.value.message

async def test_rate_limit_propagates():
    with pytest.raises(RateLimitedError):
        await generate(generator(ScriptedLLMClient([RateLimitedError("Muchas consultas.")])))

# ---------- factory ----------
def test_create_generator_uses_the_llm_with_a_key_and_the_fake_without(monkeypatch):
    for name in AI_ENV:
        monkeypatch.delenv(name, raising=False)
    assert isinstance(create_generator(), FakeDraftGenerator)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    created = create_generator()
    assert isinstance(created, LLMDraftGenerator)
    assert isinstance(created, DraftGenerator)
    monkeypatch.setenv("AI_ENABLE_LLM", "0")
    assert isinstance(create_generator(), FakeDraftGenerator)
