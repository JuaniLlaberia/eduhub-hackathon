from datetime import UTC, datetime
import pytest
from conftest import DEMO_HANDLE
from eduhub_backend.storage import SqliteStore
from eduhub_shared.models import AnalysisJob, ApiError, ErrorCode, JobStatus

OLD = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
ERROR = ApiError(code=ErrorCode.INTERNAL_ERROR, message="El análisis se interrumpió. Iniciá uno nuevo.")

def job(job_id, status, **extra):
    return AnalysisJob(
        id=job_id, handle=DEMO_HANDLE, status=status, progress=0.4, created_at=OLD, updated_at=OLD, **extra
    )

def jobs_in_every_status():
    return [
        job("q", JobStatus.QUEUED),
        job("f", JobStatus.FETCHING),
        job("a", JobStatus.ANALYZING, message="Analizando"),
        job("d", JobStatus.DONE, report_id="r1").model_copy(update={"progress": 1.0}),
        job("x", JobStatus.FAILED, error=ApiError(code=ErrorCode.ANALYSIS_FAILED, message="No hay posts.")),
    ]

@pytest.fixture
async def store(tmp_path):
    store = SqliteStore(tmp_path / "eduhub.sqlite3")
    await store.init()
    yield store
    await store.close()

async def test_unfinished_jobs_are_failed(store):
    for item in jobs_in_every_status():
        await store.save_job(item)
    assert await store.fail_unfinished_jobs(ERROR) == 3
    for job_id in ("q", "f", "a"):
        failed = await store.get_job(job_id)
        assert failed.status == JobStatus.FAILED
        assert failed.error == ERROR
        assert failed.report_id is None
        assert failed.progress == 0.4
        assert failed.created_at == OLD
        assert failed.updated_at > OLD

async def test_finished_jobs_are_untouched(store):
    originals = {j.id: j for j in jobs_in_every_status()}
    for item in originals.values():
        await store.save_job(item)
    await store.fail_unfinished_jobs(ERROR)
    assert await store.get_job("d") == originals["d"]
    assert await store.get_job("x") == originals["x"]

async def test_nothing_to_fail_returns_zero(store):
    assert await store.fail_unfinished_jobs(ERROR) == 0
    await store.save_job(job("d", JobStatus.DONE, report_id="r1"))
    assert await store.fail_unfinished_jobs(ERROR) == 0

@pytest.mark.parametrize("demo_mode", [True, False])
async def test_app_startup_fails_jobs_left_from_a_previous_run(make_client, settings, demo_mode):
    previous = SqliteStore(settings.database_path)
    await previous.init()
    await previous.save_job(job("stale", JobStatus.ANALYZING))
    await previous.save_job(job("done", JobStatus.DONE, report_id="r1"))
    await previous.close()
    async with make_client(settings.model_copy(update={"demo_mode": demo_mode})) as (client, _):
        stale = AnalysisJob.model_validate((await client.get("/analyses/stale")).json())
        assert stale.status == JobStatus.FAILED
        assert stale.error.code == ErrorCode.INTERNAL_ERROR
        assert stale.error.message.strip()
        done = AnalysisJob.model_validate((await client.get("/analyses/done")).json())
        assert done.status == JobStatus.DONE
