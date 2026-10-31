"""
Phase 1 startup wiring. The two ConfigError tests describe temporary behaviour: revoke and re-approve them when
TwitterApiIoSource exists and when the AI team delivers eduhub_ai.
"""
import pytest
from eduhub_backend.deps import ConfigError, build_deps
from eduhub_backend.sources.fixture import FixturePostSource
from eduhub_backend.storage import SqliteStore
from eduhub_shared.fakes import FakeAnalyzer, FakeAudienceSimulator, FakeDraftGenerator, FakePostPublisher

def test_fake_ai_and_demo_mode_wire_every_fake(settings):
    deps = build_deps(settings)
    assert isinstance(deps.source, FixturePostSource)
    assert isinstance(deps.analyzer, FakeAnalyzer)
    assert isinstance(deps.generator, FakeDraftGenerator)
    assert isinstance(deps.simulator, FakeAudienceSimulator)
    assert isinstance(deps.publisher, FakePostPublisher)
    assert isinstance(deps.store, SqliteStore)

def test_demo_mode_off_fails_until_a_real_source_exists(settings):
    with pytest.raises(ConfigError):
        build_deps(settings.model_copy(update={"demo_mode": False}))

def test_real_ai_fails_until_eduhub_ai_is_delivered(settings):
    with pytest.raises(ConfigError):
        build_deps(settings.model_copy(update={"eduhub_fake_ai": False}))
