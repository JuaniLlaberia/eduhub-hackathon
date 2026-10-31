"""
Startup wiring with the real eduhub_ai (EDUHUB_FAKE_AI=0). Replaces test_real_ai_fails_until_eduhub_ai_is_delivered.
The LLM is switched off so the result does not depend on the developer's OPENROUTER_API_KEY.
"""
import pytest
from eduhub_backend.api.health import feature_flags
from eduhub_backend.deps import build_deps
from eduhub_shared.fakes import FakeAnalyzer, FakeDraftGenerator

@pytest.fixture
def real_ai_settings(settings, monkeypatch):
    monkeypatch.setenv("AI_ENABLE_LLM", "0")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    return settings.model_copy(update={"eduhub_fake_ai": False})

def test_real_ai_starts_without_a_config_error(real_ai_settings):
    deps = build_deps(real_ai_settings)
    assert deps.analyzer is not None

def test_real_ai_uses_the_real_analyzer(real_ai_settings):
    deps = build_deps(real_ai_settings)
    assert not isinstance(deps.analyzer, FakeAnalyzer)

def test_real_ai_without_llm_keeps_drafts_working_with_the_fake_generator(real_ai_settings):
    deps = build_deps(real_ai_settings)
    assert isinstance(deps.generator, FakeDraftGenerator)
    assert feature_flags(real_ai_settings, deps).generation is True

def test_real_ai_without_llm_disables_simulation(real_ai_settings):
    deps = build_deps(real_ai_settings)
    assert deps.simulator is None
    assert feature_flags(real_ai_settings, deps).simulation is False
