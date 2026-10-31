"""
Builds the backend's dependencies (data source, AI, publisher, store) from Settings.
"""
from dataclasses import dataclass
from eduhub_ai import create_analyzer, create_generator, create_simulator
from eduhub_backend.settings import Settings
from eduhub_backend.sources.fixture import FixturePostSource
from eduhub_backend.storage import SqliteStore, Store
from eduhub_shared.fakes import FakeAnalyzer, FakeAudienceSimulator, FakeDraftGenerator, FakePostPublisher
from eduhub_shared.interfaces import Analyzer, AudienceSimulator, DraftGenerator, PostPublisher, PostSource

class ConfigError(Exception):
    """
    The settings ask for something this build cannot provide; raised at startup.
    """

@dataclass(frozen=True)
class Deps:
    """
    Everything create_app needs. simulator None means the simulation feature is disabled.
    """
    source: PostSource
    analyzer: Analyzer
    generator: DraftGenerator
    simulator: AudienceSimulator | None
    publisher: PostPublisher
    store: Store

def build_source(settings: Settings) -> PostSource:
    """
    Return FixturePostSource in DEMO_MODE; no real source exists yet.
    """
    if not settings.demo_mode:
        raise ConfigError("DEMO_MODE=0 needs TwitterApiIoSource, which is not implemented yet. Set DEMO_MODE=1.")
    return FixturePostSource(settings.fixtures_dir)

def build_ai(settings: Settings) -> tuple[Analyzer, DraftGenerator, AudienceSimulator | None]:
    """
    Return the fakes when EDUHUB_FAKE_AI is on, otherwise the eduhub_ai factories.
    """
    if settings.eduhub_fake_ai:
        return FakeAnalyzer(), FakeDraftGenerator(), FakeAudienceSimulator()
    try:
        return create_analyzer(), create_generator(), create_simulator()
    except NotImplementedError as error:
        raise ConfigError(f"eduhub_ai is not ready ({error}). Set EDUHUB_FAKE_AI=1.") from error

def build_deps(settings: Settings) -> Deps:
    """
    Build every dependency from settings, failing fast with ConfigError on unsupported combinations.
    """
    analyzer, generator, simulator = build_ai(settings)
    return Deps(
        source=build_source(settings),
        analyzer=analyzer,
        generator=generator,
        simulator=simulator,
        publisher=FakePostPublisher(),
        store=SqliteStore(settings.database_path),
    )
