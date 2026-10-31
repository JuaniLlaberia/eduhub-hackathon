from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import replace
from pathlib import Path
import httpx
import pytest
from asgi_lifespan import LifespanManager
from eduhub_backend.app import create_app
from eduhub_backend.deps import Deps
from eduhub_backend.settings import Settings
from eduhub_backend.sources.fixture import FixturePostSource
from eduhub_backend.storage import SqliteStore
from eduhub_shared.fakes import FakeAnalyzer, FakeAudienceSimulator, FakeDraftGenerator, FakePostPublisher
from eduhub_shared.fixtures import load_report, load_snapshot
from eduhub_shared.models import AccountSnapshot, AnalysisReport, ErrorResponse

DEMO_HANDLE = "demo_finanzas"
FRONT_ORIGIN = "http://localhost:3000"

def snapshot_for(handle: str) -> AccountSnapshot:
    snapshot = load_snapshot()
    profile = snapshot.profile.model_copy(update={"handle": handle})
    posts = [p.model_copy(update={"author_handle": handle}) for p in snapshot.posts]
    return snapshot.model_copy(update={"profile": profile, "posts": posts})

def report_for(handle: str, report_id: str) -> AnalysisReport:
    report = load_report()
    profile = report.profile.model_copy(update={"handle": handle})
    return report.model_copy(update={"id": report_id, "profile": profile})

def write_snapshot(directory: Path, snapshot: AccountSnapshot) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{snapshot.profile.handle}.json"
    path.write_text(snapshot.model_dump_json(), encoding="utf-8")
    return path

def write_report(directory: Path, report: AnalysisReport) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{report.profile.handle}.report.json"
    path.write_text(report.model_dump_json(), encoding="utf-8")
    return path

def assert_error(response: httpx.Response, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    body = ErrorResponse.model_validate(response.json())
    assert body.error.code == code
    assert body.error.message.strip()

@pytest.fixture
def fixtures_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "fixtures"
    directory.mkdir()
    return directory

@pytest.fixture
def settings(tmp_path: Path, fixtures_dir: Path) -> Settings:
    return Settings(
        _env_file=None,
        eduhub_fake_ai=True,
        demo_mode=True,
        frontend_origin=FRONT_ORIGIN,
        database_path=tmp_path / "db" / "eduhub.sqlite3",
        fixtures_dir=fixtures_dir,
    )

@pytest.fixture
def deps(settings: Settings) -> Deps:
    return Deps(
        source=FixturePostSource(settings.fixtures_dir),
        analyzer=FakeAnalyzer(),
        generator=FakeDraftGenerator(),
        simulator=FakeAudienceSimulator(),
        publisher=FakePostPublisher(),
        store=SqliteStore(settings.database_path),
    )

@pytest.fixture
def make_client(
    settings: Settings, deps: Deps
) -> Callable[..., AbstractAsyncContextManager[tuple[httpx.AsyncClient, object]]]:
    @asynccontextmanager
    async def factory(
        settings: Settings = settings, **overrides: object
    ) -> AsyncIterator[tuple[httpx.AsyncClient, object]]:
        app = create_app(settings, replace(deps, **overrides))
        async with LifespanManager(app):
            transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                yield client, app

    return factory

@pytest.fixture
async def client(make_client: Callable) -> AsyncIterator[httpx.AsyncClient]:
    async with make_client() as (client, _):
        yield client
