import pytest
from conftest import DEMO_HANDLE, assert_error
from eduhub_backend.sources.fixture import FixturePostSource
from eduhub_shared.errors import RateLimitedError, SourceUnavailableError
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.models import AnalysisJob, AnalysisReport, JobStatus
from eduhub_shared.testing import assert_report_matches_snapshot

class FailingProfileSource(FixturePostSource):
    def __init__(self, directory, error):
        super().__init__(directory)
        self.error = error

    async def fetch_profile(self, handle):
        raise self.error

async def start_and_finish(client, app, body):
    response = await client.post("/analyses", json=body)
    assert response.status_code == 202, response.text
    job = AnalysisJob.model_validate(response.json())
    await app.state.runner.wait(job.id)
    response = await client.get(f"/analyses/{job.id}")
    assert response.status_code == 200
    return AnalysisJob.model_validate(response.json())

async def test_create_analysis_returns_a_queued_job(client):
    response = await client.post("/analyses", json={"handle": DEMO_HANDLE})
    assert response.status_code == 202
    job = AnalysisJob.model_validate(response.json())
    assert job.status == JobStatus.QUEUED
    assert job.handle == DEMO_HANDLE
    assert job.progress == 0

async def test_create_analysis_normalizes_the_handle(client):
    response = await client.post("/analyses", json={"handle": "@Demo_Finanzas"})
    assert response.status_code == 202
    assert response.json()["handle"] == DEMO_HANDLE

async def test_analysis_runs_to_done_and_the_report_can_be_fetched(make_client):
    async with make_client() as (client, app):
        job = await start_and_finish(client, app, {"handle": DEMO_HANDLE})
        assert job.status == JobStatus.DONE
        assert job.progress == 1.0
        response = await client.get(f"/reports/{job.report_id}")
        assert response.status_code == 200
        report = AnalysisReport.model_validate(response.json())
        assert report.id == job.report_id
        assert_report_matches_snapshot(report, load_snapshot())

async def test_max_posts_limits_the_analyzed_posts(make_client):
    async with make_client() as (client, app):
        job = await start_and_finish(client, app, {"handle": DEMO_HANDLE, "max_posts": 10})
        report = (await client.get(f"/reports/{job.report_id}")).json()
        assert len(report["posts"]) == 10

async def test_new_analysis_becomes_the_latest_report(make_client):
    async with make_client() as (client, app):
        job = await start_and_finish(client, app, {"handle": DEMO_HANDLE})
        response = await client.get(f"/accounts/{DEMO_HANDLE}/report")
        assert response.status_code == 200
        assert AnalysisReport.model_validate(response.json()).id == job.report_id

async def test_unknown_account_is_404_before_any_job_is_created(client):
    response = await client.post("/analyses", json={"handle": "nobody"})
    assert_error(response, 404, "account_not_found")

@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (RateLimitedError("Demasiadas consultas."), 429, "rate_limited"),
        (SourceUnavailableError("La fuente no responde."), 503, "source_unavailable"),
    ],
)
async def test_source_errors_on_profile_check_are_mapped(make_client, fixtures_dir, error, status, code):
    async with make_client(source=FailingProfileSource(fixtures_dir, error)) as (client, _):
        response = await client.post("/analyses", json={"handle": DEMO_HANDLE})
        assert_error(response, status, code)
        assert response.json()["error"]["message"] == error.message

@pytest.mark.parametrize(
    "body",
    [
        {},
        {"handle": "not a handle!"},
        {"handle": DEMO_HANDLE, "max_posts": 5},
        {"handle": DEMO_HANDLE, "max_posts": 501},
        {"handle": DEMO_HANDLE, "unexpected": 1},
    ],
)
async def test_invalid_analysis_request_is_422(client, body):
    response = await client.post("/analyses", json=body)
    assert_error(response, 422, "invalid_request")

async def test_malformed_json_is_422(client):
    response = await client.post("/analyses", content=b"{not json", headers={"content-type": "application/json"})
    assert_error(response, 422, "invalid_request")

async def test_unknown_job_is_404(client):
    assert_error(await client.get("/analyses/" + "0" * 32), 404, "not_found")
