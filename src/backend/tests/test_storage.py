from datetime import UTC, datetime
import pytest
from conftest import DEMO_HANDLE, report_for
from eduhub_backend.storage import SqliteStore
from eduhub_shared.fixtures import load_report, load_snapshot
from eduhub_shared.models import AnalysisJob, JobStatus

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)

def make_job(job_id: str = "a" * 32, status: JobStatus = JobStatus.QUEUED) -> AnalysisJob:
    return AnalysisJob(id=job_id, handle=DEMO_HANDLE, status=status, progress=0, created_at=NOW, updated_at=NOW)

@pytest.fixture
async def store(tmp_path):
    store = SqliteStore(tmp_path / "nested" / "dir" / "eduhub.sqlite3")
    await store.init()
    yield store
    await store.close()

async def test_init_creates_missing_parent_directories(store, tmp_path):
    assert (tmp_path / "nested" / "dir" / "eduhub.sqlite3").exists()

async def test_job_round_trip(store):
    job = make_job()
    await store.save_job(job)
    assert await store.get_job(job.id) == job

async def test_saving_a_job_again_updates_it(store):
    await store.save_job(make_job())
    done = make_job(status=JobStatus.DONE).model_copy(update={"progress": 1.0, "report_id": "r1"})
    await store.save_job(done)
    assert await store.get_job(done.id) == done

async def test_unknown_job_is_none(store):
    assert await store.get_job("missing") is None

async def test_report_round_trip(store):
    report = load_report()
    await store.save_report(report)
    assert await store.get_report(report.id) == report

async def test_unknown_report_is_none(store):
    assert await store.get_report("missing") is None

async def test_latest_report_is_the_most_recently_stored(store):
    first = report_for(DEMO_HANDLE, "r1")
    second = report_for(DEMO_HANDLE, "r2").model_copy(update={"generated_at": datetime(2020, 1, 1, tzinfo=UTC)})
    await store.save_report(first)
    await store.save_report(second)
    assert (await store.get_latest_report(DEMO_HANDLE)).id == "r2"

async def test_latest_report_is_per_handle(store):
    await store.save_report(report_for(DEMO_HANDLE, "r1"))
    await store.save_report(report_for("alice", "r2"))
    assert (await store.get_latest_report(DEMO_HANDLE)).id == "r1"
    assert (await store.get_latest_report("alice")).id == "r2"

async def test_no_latest_report_is_none(store):
    assert await store.get_latest_report("nobody") is None

async def test_save_snapshot(store):
    await store.save_snapshot(load_snapshot())

async def test_data_persists_across_instances(tmp_path):
    path = tmp_path / "eduhub.sqlite3"
    first = SqliteStore(path)
    await first.init()
    await first.save_job(make_job())
    await first.save_report(load_report())
    await first.close()
    second = SqliteStore(path)
    await second.init()
    assert await second.get_job("a" * 32) == make_job()
    assert await second.get_latest_report(DEMO_HANDLE) == load_report()
    await second.close()
