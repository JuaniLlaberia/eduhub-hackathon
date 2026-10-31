"""
POST /simulations (stretch; 501 when no simulator is available).
"""
from typing import Annotated
from fastapi import Depends, FastAPI
from eduhub_backend.api import get_deps
from eduhub_backend.deps import Deps
from eduhub_backend.errors import HttpError
from eduhub_shared.models import ErrorCode, SimulationRequest, SimulationResult

async def create_simulation(request: SimulationRequest, deps: Annotated[Deps, Depends(get_deps)]) -> SimulationResult:
    """
    Test variants with a synthetic audience.
    """
    if deps.simulator is None:
        raise HttpError(ErrorCode.FEATURE_DISABLED, "La simulación de audiencia no está disponible.")
    return await deps.simulator.simulate(request)

def register(app: FastAPI) -> None:
    """
    Add this module's routes to app.
    """
    app.add_api_route(
        "/simulations", create_simulation,
        methods=["POST"], operation_id="createSimulation", response_model=SimulationResult
    )
