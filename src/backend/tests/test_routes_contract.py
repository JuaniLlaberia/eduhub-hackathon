from eduhub_backend.app import create_app
from eduhub_shared.testing import assert_routes_match_contract, fastapi_routes

def test_app_exposes_exactly_the_contract_routes(settings, deps):
    app = create_app(settings, deps)
    assert_routes_match_contract(fastapi_routes(app))
