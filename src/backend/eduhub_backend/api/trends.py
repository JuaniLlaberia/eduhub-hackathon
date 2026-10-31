"""
GET /trends.
"""
from typing import Annotated
from fastapi import Depends, FastAPI
from eduhub_backend.api import get_deps
from eduhub_backend.deps import Deps
from eduhub_shared.models import TrendsResponse

async def get_trends(deps: Annotated[Deps, Depends(get_deps)]) -> TrendsResponse:
    """
    Current trends in Argentina.
    """
    return TrendsResponse(trends=await deps.source.fetch_trends())

def register(app: FastAPI) -> None:
    """
    Add this module's routes to app.
    """
    app.add_api_route("/trends", get_trends, methods=["GET"], operation_id="getTrends", response_model=TrendsResponse)
