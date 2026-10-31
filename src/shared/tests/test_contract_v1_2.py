import asyncio
import json
import pytest
from pydantic import ValidationError
from eduhub_shared.fakes import FakeAnalyzer
from eduhub_shared.fixtures import load_json, load_report, load_snapshot
from eduhub_shared.models import (
    AccountSnapshot,
    AnalysisReport,
    AnalysisRequest,
    AudienceFilters,
    CreatorContext,
    CreatorGoal,
    DraftRequest,
    PreferredCta,
    SimulationRequest,
)
from eduhub_shared.models import simulation as simulation_models
from eduhub_shared.openapi import OPENAPI_PATH
from eduhub_shared.version import CONTRACT_VERSION

def test_contract_version_is_1_2_0():
    assert CONTRACT_VERSION == "1.2.0"

def test_empty_brief_is_valid_and_all_fields_are_optional():
    context = CreatorContext()
    assert context.goal is None
    assert context.goal_detail is None
    assert context.offering is None
    assert context.target_audience is None
    assert context.audience_filters == AudienceFilters()
    assert context.brand_voice is None
    assert context.avoid_topics == []
    assert context.preferred_cta is None

def test_enum_values():
    assert {g.value for g in CreatorGoal} == {"sell", "traffic", "reach", "community", "launch", "other"}
    assert {c.value for c in PreferredCta} == {"link", "reply", "save", "share", "follow", "none"}

def test_full_brief_validates():
    context = CreatorContext(
        goal="sell", goal_detail="Vender 500 ebooks", offering="Ebook 'Soy Solito'", target_audience="Gente sola",
        audience_filters={"age_groups": ["18 a 29 años"], "genders": [], "provinces": []},
        brand_voice="Cercana y con humor", avoid_topics=["política"], preferred_cta="link",
    )
    assert context.goal is CreatorGoal.SELL
    assert context.preferred_cta is PreferredCta.LINK
    assert context.audience_filters.age_groups == ["18 a 29 años"]

@pytest.mark.parametrize("fields", [
    {"goal_detail": "x" * 301},
    {"offering": "x" * 501},
    {"target_audience": "x" * 301},
    {"brand_voice": "x" * 301},
    {"avoid_topics": [f"tema {i}" for i in range(11)]},
    {"avoid_topics": ["x" * 61]},
    {"goal": "ganar"},
    {"preferred_cta": "dm"},
    {"unknown_field": "x"},
])
def test_brief_limits_and_unknown_values_are_rejected(fields):
    with pytest.raises(ValidationError):
        CreatorContext(**fields)

@pytest.mark.parametrize("model", [AnalysisRequest, DraftRequest, SimulationRequest])
def test_requests_accept_an_optional_brief(model):
    base = {"handle": "demo_finanzas"} if model is not SimulationRequest else {"variants": ["hola"]}
    assert model(**base).context is None
    assert model(**base, context={"goal": "reach"}).context.goal is CreatorGoal.REACH

def test_snapshot_and_report_accept_an_optional_brief():
    snapshot = load_snapshot()
    without = snapshot.model_dump(mode="json")
    without.pop("context", None)
    assert AccountSnapshot.model_validate(without).context is None
    report = load_report().model_dump(mode="json")
    report.pop("context", None)
    assert AnalysisReport.model_validate(report).context is None

def test_audience_filters_moved_but_is_the_same_class():
    assert simulation_models.AudienceFilters is AudienceFilters

def test_fake_analyzer_echoes_the_brief():
    snapshot = load_snapshot()
    brief = CreatorContext(goal="community", offering="Newsletter semanal")
    report = asyncio.run(FakeAnalyzer().analyze(snapshot.model_copy(update={"context": brief})))
    assert report.context == brief
    plain = asyncio.run(FakeAnalyzer().analyze(snapshot.model_copy(update={"context": None})))
    assert plain.context is None

def test_fixtures_carry_an_example_brief():
    snapshot = load_snapshot()
    assert snapshot.context is not None
    assert snapshot.context.goal is CreatorGoal.SELL
    assert snapshot.context.offering
    assert load_report().context == snapshot.context
    assert load_json("account_snapshot.json")["context"]["goal"] == "sell"

def test_openapi_exposes_the_brief():
    schemas = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))["components"]["schemas"]
    assert {"CreatorContext", "CreatorGoal", "PreferredCta"} <= set(schemas)
    for name in ("AnalysisRequest", "AnalysisReport", "DraftRequest", "SimulationRequest"):
        assert "context" in schemas[name]["properties"], name

def test_openapi_schema_names_do_not_split_into_input_and_output():
    schemas = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))["components"]["schemas"]
    assert not [name for name in schemas if name.endswith(("-Input", "-Output"))]
    assert "AudienceFilters" in schemas
