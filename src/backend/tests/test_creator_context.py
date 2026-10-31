from conftest import DEMO_HANDLE, assert_error
from eduhub_shared.fakes import FakeAnalyzer
from eduhub_shared.models import AnalysisJob, AnalysisReport, CreatorContext, JobStatus

BRIEF = {
    "goal": "sell",
    "offering": "Curso online de finanzas personales",
    "target_audience": "Jóvenes que empiezan a trabajar",
    "audience_filters": {"age_groups": ["18 a 29 años"], "genders": [], "provinces": []},
    "avoid_topics": ["política"],
    "preferred_cta": "link",
}

class RecordingAnalyzer(FakeAnalyzer):
    def __init__(self):
        super().__init__()
        self.snapshots = []

    async def analyze(self, snapshot, on_progress=None):
        self.snapshots.append(snapshot)
        return await super().analyze(snapshot, on_progress)

class RecordingGenerator:
    def __init__(self, inner):
        self.inner = inner
        self.requests = []

    async def generate(self, request, report, trends):
        self.requests.append(request)
        return await self.inner.generate(request, report, trends)

class RecordingSimulator:
    def __init__(self, inner):
        self.inner = inner
        self.requests = []

    async def simulate(self, request):
        self.requests.append(request)
        return await self.inner.simulate(request)

async def analyze(client, app, body):
    response = await client.post("/analyses", json=body)
    assert response.status_code == 202, response.text
    job = AnalysisJob.model_validate(response.json())
    await app.state.runner.wait(job.id)
    job = AnalysisJob.model_validate((await client.get(f"/analyses/{job.id}")).json())
    assert job.status == JobStatus.DONE, job
    return job

async def test_the_brief_reaches_the_analyzer_and_the_report(make_client):
    analyzer = RecordingAnalyzer()
    async with make_client(analyzer=analyzer) as (client, app):
        job = await analyze(client, app, {"handle": DEMO_HANDLE, "context": BRIEF})
        report = AnalysisReport.model_validate((await client.get(f"/reports/{job.report_id}")).json())
        latest = AnalysisReport.model_validate((await client.get(f"/accounts/{DEMO_HANDLE}/report")).json())
    expected = CreatorContext.model_validate(BRIEF)
    assert analyzer.snapshots[0].context == expected
    assert report.context == expected
    assert latest.context == expected

async def test_without_a_brief_the_snapshot_has_none(make_client):
    analyzer = RecordingAnalyzer()
    async with make_client(analyzer=analyzer) as (client, app):
        job = await analyze(client, app, {"handle": DEMO_HANDLE})
        report = AnalysisReport.model_validate((await client.get(f"/reports/{job.report_id}")).json())
    assert analyzer.snapshots[0].context is None
    assert report.context is None

async def test_an_invalid_brief_is_a_422(client):
    response = await client.post("/analyses", json={"handle": DEMO_HANDLE, "context": {"offering": "x" * 501}})
    assert_error(response, 422, "invalid_request")
    response = await client.post("/analyses", json={"handle": DEMO_HANDLE, "context": {"goal": "ganar"}})
    assert_error(response, 422, "invalid_request")

async def test_drafts_pass_the_brief_override_to_the_generator(make_client, deps):
    generator = RecordingGenerator(deps.generator)
    async with make_client(generator=generator) as (client, _):
        with_brief = await client.post("/drafts", json={"handle": DEMO_HANDLE, "context": BRIEF})
        without = await client.post("/drafts", json={"handle": DEMO_HANDLE})
    assert with_brief.status_code == 200
    assert without.status_code == 200
    assert generator.requests[0].context == CreatorContext.model_validate(BRIEF)
    assert generator.requests[1].context is None

async def test_simulations_pass_the_brief_to_the_simulator(make_client, deps):
    simulator = RecordingSimulator(deps.simulator)
    body = {"variants": ["¿Llevás un presupuesto?", "Mi planilla gratis 📊"], "context": BRIEF}
    async with make_client(simulator=simulator) as (client, _):
        response = await client.post("/simulations", json=body)
    assert response.status_code == 200, response.text
    assert simulator.requests[0].context == CreatorContext.model_validate(BRIEF)
