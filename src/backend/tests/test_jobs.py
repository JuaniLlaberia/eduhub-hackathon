import asyncio
import re
import pytest
from conftest import DEMO_HANDLE
from eduhub_backend.jobs import JobRunner
from eduhub_backend.sources.fixture import FixturePostSource
from eduhub_backend.storage import SqliteStore
from eduhub_shared.errors import AnalysisError, SourceUnavailableError
from eduhub_shared.fakes import FakeAnalyzer
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.models import AnalysisRequest, JobStatus
from eduhub_shared.testing import assert_report_matches_snapshot

class JobRef:
    def __init__(self):
        self.id = None
        self.ready = asyncio.Event()

    async def current(self, store):
        await self.ready.wait()
        return await store.get_job(self.id)

class SpySource(FixturePostSource):
    def __init__(self, directory, store, fail_with=None):
        super().__init__(directory)
        self.store = store
        self.ref = JobRef()
        self.fail_with = fail_with
        self.limits = []
        self.statuses = []

    async def fetch_posts(self, handle, limit):
        self.limits.append(limit)
        self.statuses.append((await self.ref.current(self.store)).status)
        if self.fail_with:
            raise self.fail_with
        return await super().fetch_posts(handle, limit)

class SpyAnalyzer:
    def __init__(self, store, fail_with=None):
        self.store = store
        self.ref = JobRef()
        self.fail_with = fail_with
        self.seen = []

    async def analyze(self, snapshot, on_progress=None):
        job = await self.ref.current(self.store)
        self.seen.append((job.status, job.progress, job.message))
        await on_progress(0.5, "Analizando")
        job = await self.store.get_job(self.ref.id)
        self.seen.append((job.status, job.progress, job.message))
        if self.fail_with:
            raise self.fail_with
        return await FakeAnalyzer().analyze(snapshot, None)

@pytest.fixture
async def store(tmp_path):
    store = SqliteStore(tmp_path / "eduhub.sqlite3")
    await store.init()
    yield store
    await store.close()

async def run(store, source, analyzer, max_posts=200):
    runner = JobRunner(store, source, analyzer)
    profile = await source.fetch_profile(DEMO_HANDLE)
    job = await runner.start(AnalysisRequest(handle=DEMO_HANDLE, max_posts=max_posts), profile)
    for spy in (source, analyzer):
        spy.ref.id = job.id
        spy.ref.ready.set()
    await runner.wait(job.id)
    return job, await store.get_job(job.id)

async def test_start_returns_a_stored_queued_job(store, fixtures_dir):
    runner = JobRunner(store, FixturePostSource(fixtures_dir), FakeAnalyzer())
    profile = await FixturePostSource(fixtures_dir).fetch_profile(DEMO_HANDLE)
    job = await runner.start(AnalysisRequest(handle=DEMO_HANDLE), profile)
    assert job.status == JobStatus.QUEUED
    assert job.progress == 0
    assert job.handle == DEMO_HANDLE
    assert re.fullmatch(r"[0-9a-f]{32}", job.id)
    assert (await store.get_job(job.id)).id == job.id
    await runner.wait(job.id)

async def test_successful_job_goes_through_every_status(store, fixtures_dir):
    source = SpySource(fixtures_dir, store)
    analyzer = SpyAnalyzer(store)
    _, final = await run(store, source, analyzer)
    assert source.statuses == [JobStatus.FETCHING]
    assert [s for s, _, _ in analyzer.seen] == [JobStatus.ANALYZING, JobStatus.ANALYZING]
    assert analyzer.seen[1][2] == "Analizando"
    assert final.status == JobStatus.DONE
    assert final.progress == 1.0
    assert final.error is None
    assert final.report_id is not None

async def test_progress_never_goes_backwards(store, fixtures_dir):
    analyzer = SpyAnalyzer(store)
    _, final = await run(store, SpySource(fixtures_dir, store), analyzer)
    values = [p for _, p, _ in analyzer.seen] + [final.progress]
    assert values == sorted(values)
    assert all(0 <= v <= 1 for v in values)

async def test_done_job_stores_the_analyzer_report_under_its_own_id(store, fixtures_dir):
    _, final = await run(store, SpySource(fixtures_dir, store), SpyAnalyzer(store))
    report = await store.get_report(final.report_id)
    assert report is not None
    assert report.id == final.report_id
    assert (await store.get_latest_report(DEMO_HANDLE)).id == report.id
    assert_report_matches_snapshot(report, load_snapshot())

async def test_max_posts_is_passed_as_limit(store, fixtures_dir):
    source = SpySource(fixtures_dir, store)
    _, final = await run(store, source, SpyAnalyzer(store), max_posts=10)
    assert source.limits == [10]
    assert len((await store.get_report(final.report_id)).posts) == 10

async def test_analysis_error_fails_the_job_with_its_code_and_message(store, fixtures_dir):
    analyzer = SpyAnalyzer(store, fail_with=AnalysisError("No hay suficientes posts."))
    _, final = await run(store, SpySource(fixtures_dir, store), analyzer)
    assert final.status == JobStatus.FAILED
    assert final.report_id is None
    assert final.error.code == "analysis_failed"
    assert final.error.message == "No hay suficientes posts."

async def test_source_error_fails_the_job(store, fixtures_dir):
    source = SpySource(fixtures_dir, store, fail_with=SourceUnavailableError("La fuente no responde."))
    _, final = await run(store, source, SpyAnalyzer(store))
    assert final.status == JobStatus.FAILED
    assert final.error.code == "source_unavailable"

async def test_unexpected_error_fails_the_job_as_internal_error(store, fixtures_dir):
    analyzer = SpyAnalyzer(store, fail_with=RuntimeError("boom"))
    _, final = await run(store, SpySource(fixtures_dir, store), analyzer)
    assert final.status == JobStatus.FAILED
    assert final.error.code == "internal_error"
    assert final.error.message.strip()
    assert "boom" not in final.error.message

async def test_wait_all_waits_for_every_job(store, fixtures_dir):
    runner = JobRunner(store, FixturePostSource(fixtures_dir), FakeAnalyzer())
    profile = await FixturePostSource(fixtures_dir).fetch_profile(DEMO_HANDLE)
    jobs = [await runner.start(AnalysisRequest(handle=DEMO_HANDLE), profile) for _ in range(3)]
    await runner.wait_all()
    for job in jobs:
        assert (await store.get_job(job.id)).status == JobStatus.DONE
