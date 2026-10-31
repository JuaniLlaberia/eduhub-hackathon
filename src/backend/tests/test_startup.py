"""
Startup wiring with EDUHUB_FAKE_AI=1 and DEMO_MODE=1. The real source and the real AI are covered by
test_startup_real_source.py and test_startup_real_ai.py, which replaced the temporary ConfigError tests.
"""
from eduhub_backend.deps import build_deps
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
