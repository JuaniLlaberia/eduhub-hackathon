from datetime import UTC, datetime
import pytest
from pydantic import ValidationError
from eduhub_shared.models import (
    AnalysisRequest,
    DraftRequest,
    PostMetrics,
    PublishRequest,
    SimulationRequest,
    Trend,
    normalize_handle,
)

@pytest.mark.parametrize("raw", ["@Demo_Finanzas", " demo_finanzas ", "DEMO_FINANZAS"])
def test_handles_are_normalized(raw):
    assert normalize_handle(raw) == "demo_finanzas"

@pytest.mark.parametrize("raw", ["", "@", "with space", "bad-dash", "x" * 31])
def test_invalid_handles_are_rejected(raw):
    with pytest.raises(ValueError):
        normalize_handle(raw)

def test_request_models_normalize_handles():
    assert AnalysisRequest(handle="@Demo_Finanzas").handle == "demo_finanzas"
    assert DraftRequest(handle="@A").handle == "a"

def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate({"handle": "demo", "unexpected": 1})

def test_datetimes_must_be_timezone_aware():
    with pytest.raises(ValidationError):
        Trend(name="x", observed_at=datetime(2026, 10, 30, 12, 0))
    assert Trend(name="x", observed_at=datetime(2026, 10, 30, 12, 0, tzinfo=UTC)).location == "Argentina"

def test_metrics_reject_negative_counters():
    with pytest.raises(ValidationError):
        PostMetrics(impressions=10, likes=-1, reposts=0, quotes=0, replies=0, bookmarks=0)

def test_impressions_may_be_missing_but_must_be_explicit():
    assert PostMetrics(impressions=None, likes=0, reposts=0, quotes=0, replies=0, bookmarks=0).impressions is None
    with pytest.raises(ValidationError):
        PostMetrics.model_validate({"likes": 0, "reposts": 0, "quotes": 0, "replies": 0, "bookmarks": 0})

@pytest.mark.parametrize("count", [0, 6])
def test_draft_count_is_bounded(count):
    with pytest.raises(ValidationError):
        DraftRequest(handle="demo", count=count)

def test_analysis_request_defaults_and_bounds():
    assert AnalysisRequest(handle="demo").max_posts == 200
    with pytest.raises(ValidationError):
        AnalysisRequest(handle="demo", max_posts=501)

def test_simulation_accepts_one_to_three_variants():
    assert SimulationRequest(variants=["a"]).audience_size == 50
    with pytest.raises(ValidationError):
        SimulationRequest(variants=[])
    with pytest.raises(ValidationError):
        SimulationRequest(variants=["a", "b", "c", "d"])

def test_publish_text_must_not_be_empty():
    with pytest.raises(ValidationError):
        PublishRequest(handle="demo", text="")
