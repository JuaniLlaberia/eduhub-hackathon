import pytest
from conftest import FRONT_ORIGIN, assert_error
from eduhub_backend.sources.fixture import FixturePostSource
from eduhub_shared.errors import SourceUnavailableError
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.models import FeatureFlags, HealthResponse, TrendsResponse
from eduhub_shared.version import CONTRACT_VERSION

class FailingTrendsSource(FixturePostSource):
    async def fetch_trends(self, location="Argentina"):
        raise SourceUnavailableError("No pudimos obtener las tendencias.")

async def test_health_reports_the_contract_version(client):
    response = await client.get("/health")
    assert response.status_code == 200
    health = HealthResponse.model_validate(response.json())
    assert health.status == "ok"
    assert health.contract_version == CONTRACT_VERSION

async def test_features_with_every_fake_enabled(client):
    response = await client.get("/features")
    assert response.status_code == 200
    assert FeatureFlags.model_validate(response.json()) == FeatureFlags(
        generation=True, publishing=True, simulation=True, demo_mode=True
    )

async def test_features_report_simulation_off_without_a_simulator(make_client):
    async with make_client(simulator=None) as (client, _):
        flags = FeatureFlags.model_validate((await client.get("/features")).json())
        assert flags.simulation is False
        assert flags.generation is True
        assert flags.publishing is True

async def test_features_report_demo_mode_off(make_client, settings):
    async with make_client(settings.model_copy(update={"demo_mode": False})) as (client, _):
        assert (await client.get("/features")).json()["demo_mode"] is False

async def test_trends(client):
    response = await client.get("/trends")
    assert response.status_code == 200
    assert TrendsResponse.model_validate(response.json()).trends == load_snapshot().trends

async def test_trends_source_unavailable_is_503(make_client, fixtures_dir):
    async with make_client(source=FailingTrendsSource(fixtures_dir)) as (client, _):
        assert_error(await client.get("/trends"), 503, "source_unavailable")

async def test_unknown_path_is_an_error_response(client):
    assert_error(await client.get("/does-not-exist"), 404, "not_found")

async def test_cors_allows_the_front_origin(client):
    response = await client.options(
        "/health", headers={"origin": FRONT_ORIGIN, "access-control-request-method": "GET"}
    )
    assert response.headers.get("access-control-allow-origin") == FRONT_ORIGIN

@pytest.mark.parametrize("origin", ["http://a.test", "https://b.test"])
async def test_cors_allows_every_listed_origin(make_client, settings, origin):
    custom = settings.model_copy(update={"frontend_origin": "http://a.test,https://b.test"})
    async with make_client(custom) as (client, _):
        response = await client.get("/health", headers={"origin": origin})
        assert response.headers.get("access-control-allow-origin") == origin

async def test_cors_rejects_other_origins(client):
    response = await client.get("/health", headers={"origin": "https://evil.test"})
    assert "access-control-allow-origin" not in response.headers
