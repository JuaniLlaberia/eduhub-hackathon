"""
Stage 09: audience sandbox. Personas from the ENCC 2022-23 X users (OpenARG), LLM reactions per batch of
personas, aggregation with the survey weights. All LLM calls are scripted.
"""
import json
import re
from datetime import UTC, datetime
import pytest
from eduhub_ai import create_simulator
from eduhub_ai.config import load_settings
from eduhub_ai.llm.client import LLMCall, LLMError
from eduhub_ai.llm.scripted import ScriptedLLMClient
from eduhub_ai.sandbox import personas as personas_module
from eduhub_ai.sandbox.personas import load_personas, sample_personas
from eduhub_ai.sandbox.prompts import SANDBOX_SYSTEM
from eduhub_ai.sandbox.simulator import DISCLAIMER, LLMAudienceSimulator, ReactionsResponse
from eduhub_shared.errors import SimulationError
from eduhub_shared.interfaces import AudienceSimulator
from eduhub_shared.models import AudienceDimension, AudienceFilters, Persona, SimulationRequest
from eduhub_shared.testing import check_simulator

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
SETTINGS = load_settings({})

def payload_of(call: LLMCall) -> dict:
    return json.loads(call.user.split("\n", 1)[1])

class Audience:
    """
    Scripted LLM: every persona reacts to every variant with react(persona, variant_index) (None = omitted).
    """
    def __init__(self, react=None, fail_batches: int = 0) -> None:
        self.react = react or (lambda persona, index: "like" if index == 0 else "read")
        self.fail_batches = fail_batches
        self.calls: list[LLMCall] = []

    def __call__(self, call: LLMCall) -> str:
        self.calls.append(call)
        if len(self.calls) <= self.fail_batches:
            raise LLMError("down")
        payload = payload_of(call)
        reactions = []
        for persona in payload["personas"]:
            for variant in payload["variantes"]:
                reaction = self.react(persona, variant["indice"])
                if reaction is not None:
                    reactions.append({"persona_id": persona["id"], "variant_index": variant["indice"],
                                      "reaction": reaction, "comment": None, "sentiment": 0.1})
        return json.dumps({"reactions": reactions})

def simulator(audience: Audience, personas: list[Persona] | None = None) -> LLMAudienceSimulator:
    return LLMAudienceSimulator(SETTINGS, ScriptedLLMClient([audience] * 30), clock=lambda: NOW, personas=personas)

def persona(pid: str, weight: float, age: str = "18 a 29 años", gender: str = "Mujer") -> Persona:
    return Persona(id=pid, age_group=age, gender=gender, province="Buenos Aires", socioeconomic_level="Medio",
                   platforms=["x"], traits=["publica contenido todas las semanas"], weight=weight)

# ---------- personas ----------
def test_load_personas_are_valid_weighted_and_anonymous():
    personas = load_personas()
    assert len(personas) == 492
    assert all(p.weight > 0 for p in personas)
    assert all(re.fullmatch(r"persona-\d{3}", p.id) for p in personas)
    assert len({p.id for p in personas}) == len(personas)
    assert all("x" in p.platforms and p.traits for p in personas)
    assert {p.socioeconomic_level for p in personas} <= {"Alto", "Medio", "Bajo", None}

def test_sample_is_deterministic_and_respects_filters():
    personas = load_personas()
    filters = AudienceFilters(age_groups=["18 a 29 años"], genders=["Mujer"])
    first = sample_personas(personas, filters, 20, seed=7)
    assert first == sample_personas(personas, filters, 20, seed=7)
    assert first != sample_personas(personas, filters, 20, seed=8)
    assert len(first) == 20
    assert len({p.id for p in first}) == 20
    assert all(p.age_group == "18 a 29 años" and p.gender == "Mujer" for p in first)
    caba = sample_personas(personas, AudienceFilters(provinces=["Ciudad Autónoma de Buenos Aires"]), 10, seed=0)
    assert all(p.province == "Ciudad Autónoma de Buenos Aires" for p in caba)

def test_sample_caps_at_the_pool_size_and_empty_filters_mean_everyone():
    personas = [persona(f"p{i}", 1.0) for i in range(5)]
    assert len(sample_personas(personas, AudienceFilters(), 50, seed=0)) == 5
    assert sample_personas(personas, AudienceFilters(provinces=["Tierra del Fuego"]), 10, seed=0) == []

# ---------- contract ----------
async def test_contract_with_scripted_llm():
    result = await check_simulator(simulator(Audience()))
    assert result.best_variant_index == 0
    assert result.disclaimer == DISCLAIMER
    assert "no predice" in result.disclaimer
    assert result.summary

async def test_batches_of_ten_personas_with_every_variant():
    audience = Audience()
    sim = simulator(audience)
    await sim.simulate(SimulationRequest(variants=["A", "B", "C"], audience_size=25))
    assert len(audience.calls) == 3
    assert sorted(len(payload_of(c)["personas"]) for c in audience.calls) == [5, 10, 10]
    assert all([v["texto"] for v in payload_of(c)["variantes"]] == ["A", "B", "C"] for c in audience.calls)
    assert all(c.system == SANDBOX_SYSTEM and issubclass(c.schema, ReactionsResponse) for c in audience.calls)
    assert all(c.model == SETTINGS.label_model for c in audience.calls)
    assert not re.search(r"\b20\d\d\b", SANDBOX_SYSTEM)

# ---------- aggregation ----------
async def test_heavily_weighted_personas_decide_the_winner():
    personas = [persona("heavy", 100.0, age="30 a 49 años"), persona("light-1", 1.0), persona("light-2", 1.0)]

    def react(p: dict, index: int) -> str:
        if p["id"] == "heavy":
            return "like" if index == 1 else "ignore"
        return "like" if index == 0 else "ignore"

    result = await simulator(Audience(react), personas).simulate(
        SimulationRequest(variants=["uno", "dos"], audience_size=5))
    by_index = {v.variant_index: v for v in result.variants}
    assert by_index[0].reaction_counts["like"] == 2
    assert by_index[1].reaction_counts["like"] == 1
    assert by_index[1].interaction_rate == pytest.approx(100 / 102)
    assert by_index[0].interaction_rate == pytest.approx(2 / 102)
    assert result.best_variant_index == 1
    segment = {(s.dimension, s.value, s.variant_index): s for s in result.segments}
    adults = segment[(AudienceDimension.AGE_GROUP, "30 a 49 años", 1)]
    young = segment[(AudienceDimension.AGE_GROUP, "18 a 29 años", 1)]
    assert (adults.persona_count, adults.interaction_rate) == (1, 1.0)
    assert (young.persona_count, young.interaction_rate) == (2, 0.0)
    assert {s.dimension for s in result.segments} == set(AudienceDimension)

async def test_unknown_or_repeated_reactions_are_ignored():
    personas = [persona("a", 1.0), persona("b", 1.0)]

    class Noisy(Audience):
        def __call__(self, call: LLMCall) -> str:
            base = json.loads(super().__call__(call))["reactions"]
            extra = [dict(base[0], reaction="ignore"), dict(base[0], persona_id="ghost"),
                     dict(base[0], variant_index=7)]
            return json.dumps({"reactions": [*base, *extra]})

    result = await simulator(Noisy(), personas).simulate(SimulationRequest(variants=["uno"], audience_size=5))
    assert len(result.reactions) == 2
    assert {r.persona_id for r in result.reactions} == {"a", "b"}
    assert all(r.reaction == "like" for r in result.reactions)

# ---------- failures ----------
async def test_more_than_half_missing_raises_simulation_error():
    with pytest.raises(SimulationError) as info:
        await simulator(Audience(fail_batches=2)).simulate(SimulationRequest(variants=["uno"], audience_size=30))
    assert info.value.message

async def test_a_failed_batch_is_tolerated_when_most_reactions_arrive():
    result = await simulator(Audience(fail_batches=1)).simulate(SimulationRequest(variants=["uno"], audience_size=30))
    assert len(result.reactions) == 20

async def test_no_personas_for_the_filters_raises_simulation_error():
    request = SimulationRequest(variants=["uno"], audience_size=10,
                                filters=AudienceFilters(provinces=["Atlántida"]))
    with pytest.raises(SimulationError):
        await simulator(Audience()).simulate(request)

# ---------- factory ----------
def test_create_simulator_needs_a_key_and_the_personas_file(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("AI_ENABLE_LLM", raising=False)
    assert create_simulator() is None
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    created = create_simulator()
    assert isinstance(created, LLMAudienceSimulator)
    assert isinstance(created, AudienceSimulator)
    monkeypatch.setattr(personas_module, "PERSONAS_PATH", tmp_path / "missing.json")
    assert create_simulator() is None
