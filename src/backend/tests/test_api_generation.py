from datetime import UTC, datetime
import pytest
from conftest import DEMO_HANDLE, assert_error
from eduhub_shared.errors import GenerationError, RateLimitedError, SimulationError
from eduhub_shared.fixtures import load_report, load_snapshot
from eduhub_shared.models import DraftsResponse, PublishResult, PublishStatus, SimulationResult

class RecordingGenerator:
    def __init__(self, inner):
        self.inner = inner
        self.calls = []

    async def generate(self, request, report, trends):
        self.calls.append((request, report, trends))
        return await self.inner.generate(request, report, trends)

class FailingGenerator:
    def __init__(self, error):
        self.error = error

    async def generate(self, request, report, trends):
        raise self.error

class FailingSimulator:
    def __init__(self, error):
        self.error = error

    async def simulate(self, request):
        raise self.error

SIMULATION_BODY = {"variants": ["¿Llevás un presupuesto mensual?", "Mi planilla de presupuesto, gratis 📊"]}

async def test_drafts_for_an_account_with_a_report(client):
    response = await client.post("/drafts", json={"handle": DEMO_HANDLE, "count": 2})
    assert response.status_code == 200
    drafts = DraftsResponse.model_validate(response.json()).drafts
    assert len(drafts) == 2

async def test_drafts_use_the_latest_report_and_current_trends(make_client, deps):
    generator = RecordingGenerator(deps.generator)
    async with make_client(generator=generator) as (client, _):
        response = await client.post("/drafts", json={"handle": "@Demo_Finanzas", "topic": "ahorro"})
        assert response.status_code == 200
    request, report, trends = generator.calls[0]
    assert request.topic == "ahorro"
    assert report == load_report()
    assert trends == load_snapshot().trends

async def test_drafts_without_a_report_is_404(make_client, settings):
    async with make_client(settings.model_copy(update={"demo_mode": False})) as (client, _):
        assert_error(await client.post("/drafts", json={"handle": DEMO_HANDLE}), 404, "not_found")

@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (GenerationError("No pudimos generar borradores."), 500, "generation_failed"),
        (RateLimitedError("Demasiadas consultas."), 429, "rate_limited"),
    ],
)
async def test_generator_errors_are_mapped(make_client, error, status, code):
    async with make_client(generator=FailingGenerator(error)) as (client, _):
        response = await client.post("/drafts", json={"handle": DEMO_HANDLE})
        assert_error(response, status, code)
        assert response.json()["error"]["message"] == error.message

async def test_unexpected_errors_are_500_internal_error_without_details(make_client):
    async with make_client(generator=FailingGenerator(RuntimeError("secret detail"))) as (client, _):
        response = await client.post("/drafts", json={"handle": DEMO_HANDLE})
        assert_error(response, 500, "internal_error")
        assert "secret detail" not in response.text

@pytest.mark.parametrize("body", [{"handle": DEMO_HANDLE, "count": 0}, {"handle": DEMO_HANDLE, "count": 6}, {}])
async def test_invalid_draft_request_is_422(client, body):
    assert_error(await client.post("/drafts", json=body), 422, "invalid_request")

async def test_publish_now_returns_an_intent_url(client):
    response = await client.post("/publications", json={"handle": DEMO_HANDLE, "text": "Hola mundo"})
    assert response.status_code == 200
    result = PublishResult.model_validate(response.json())
    assert result.status == PublishStatus.INTENT
    assert result.url.startswith("https://x.com/intent/post?text=")

async def test_publish_scheduled(client):
    when = datetime(2026, 11, 2, 14, 0, tzinfo=UTC)
    body = {"handle": DEMO_HANDLE, "text": "Hola mundo", "scheduled_for": when.isoformat()}
    response = await client.post("/publications", json=body)
    assert response.status_code == 200
    result = PublishResult.model_validate(response.json())
    assert result.status == PublishStatus.SCHEDULED
    assert result.scheduled_for == when

@pytest.mark.parametrize(
    "body",
    [
        {"handle": DEMO_HANDLE, "text": ""},
        {"handle": DEMO_HANDLE},
        {"handle": DEMO_HANDLE, "text": "x", "scheduled_for": "2026-11-02T14:00:00"},
    ],
)
async def test_invalid_publish_request_is_422(client, body):
    assert_error(await client.post("/publications", json=body), 422, "invalid_request")

async def test_simulation(client):
    response = await client.post("/simulations", json=SIMULATION_BODY)
    assert response.status_code == 200
    result = SimulationResult.model_validate(response.json())
    assert [v.variant_index for v in result.variants] == [0, 1]

async def test_simulation_disabled_is_501(make_client):
    async with make_client(simulator=None) as (client, _):
        assert_error(await client.post("/simulations", json=SIMULATION_BODY), 501, "feature_disabled")

async def test_simulation_error_is_mapped(make_client):
    error = SimulationError("No pudimos simular la audiencia.")
    async with make_client(simulator=FailingSimulator(error)) as (client, _):
        assert_error(await client.post("/simulations", json=SIMULATION_BODY), 500, "simulation_failed")

@pytest.mark.parametrize(
    "body", [{"variants": []}, {"variants": ["a", "b", "c", "d"]}, {"variants": ["a"], "audience_size": 1}]
)
async def test_invalid_simulation_request_is_422(client, body):
    assert_error(await client.post("/simulations", json=body), 422, "invalid_request")
