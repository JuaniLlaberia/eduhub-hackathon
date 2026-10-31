"""
GET /health and GET /features.
"""
from typing import Annotated
from fastapi import Depends, FastAPI
from eduhub_backend.api import get_deps, get_settings
from eduhub_backend.deps import Deps
from eduhub_backend.settings import Settings
from eduhub_shared.models import FeatureFlags, HealthResponse
from eduhub_shared.version import CONTRACT_VERSION

def feature_flags(settings: Settings, deps: Deps) -> FeatureFlags:
    """
    Return the enabled features: generation and publishing always, simulation when a simulator exists.
    """
    return FeatureFlags(
        generation=True, publishing=True, simulation=deps.simulator is not None, demo_mode=settings.demo_mode
    )

async def get_health() -> HealthResponse:
    """
    Liveness and the contract version this backend implements.
    """
    return HealthResponse(contract_version=CONTRACT_VERSION)

async def get_features(
    settings: Annotated[Settings, Depends(get_settings)], deps: Annotated[Deps, Depends(get_deps)]
) -> FeatureFlags:
    """
    Enabled optional features.
    """
    return feature_flags(settings, deps)

def register(app: FastAPI) -> None:
    """
    Add this module's routes to app.
    """
    app.add_api_route("/health", get_health, methods=["GET"], operation_id="getHealth", response_model=HealthResponse)
    app.add_api_route(
        "/features", get_features, methods=["GET"], operation_id="getFeatures", response_model=FeatureFlags
    )
