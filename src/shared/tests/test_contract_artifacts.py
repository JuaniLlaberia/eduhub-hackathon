import asyncio
import json
import pytest
from eduhub_shared.fixtures import FIXTURE_MODELS, FIXTURES_DIR, load_json
from eduhub_shared.fixtures.build import build_all, render
from eduhub_shared.openapi import OPENAPI_PATH, render_openapi
from eduhub_shared.routes import ROUTES
from eduhub_shared.version import CONTRACT_VERSION

def test_committed_openapi_matches_models_and_routes():
    assert OPENAPI_PATH.read_text(encoding="utf-8") == render_openapi(), "run: python -m eduhub_shared.openapi"

def test_openapi_lists_every_route_with_its_version():
    document = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert document["info"]["version"] == CONTRACT_VERSION
    for route in ROUTES:
        operation = document["paths"][route.path][route.method.lower()]
        assert operation["operationId"] == route.operation_id
        assert str(route.status_code) in operation["responses"]

def test_every_fixture_file_is_registered():
    on_disk = {p.name for p in FIXTURES_DIR.glob("*.json")}
    assert on_disk == set(FIXTURE_MODELS)

@pytest.mark.parametrize("name", sorted(FIXTURE_MODELS))
def test_fixtures_validate_against_their_model(name):
    FIXTURE_MODELS[name].model_validate(load_json(name))

def test_committed_fixtures_are_up_to_date():
    built = asyncio.run(build_all())
    outdated = [n for n, m in built.items() if (FIXTURES_DIR / n).read_text(encoding="utf-8") != render(m)]
    assert not outdated, f"run: python -m eduhub_shared.fixtures.build ({outdated})"
