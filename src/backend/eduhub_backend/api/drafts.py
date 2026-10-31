"""
POST /drafts.
"""
from typing import Annotated
from fastapi import Depends, FastAPI
from eduhub_backend.api import get_deps
from eduhub_backend.api.reports import latest_report
from eduhub_backend.deps import Deps
from eduhub_shared.models import DraftRequest, DraftsResponse

async def create_drafts(request: DraftRequest, deps: Annotated[Deps, Depends(get_deps)]) -> DraftsResponse:
    """
    Generate drafts in the creator's voice from their latest report and the current trends.
    """
    report = await latest_report(deps.store, request.handle)
    trends = await deps.source.fetch_trends()
    return DraftsResponse(drafts=await deps.generator.generate(request, report, trends))

def register(app: FastAPI) -> None:
    """
    Add this module's routes to app.
    """
    app.add_api_route(
        "/drafts", create_drafts, methods=["POST"], operation_id="createDrafts", response_model=DraftsResponse
    )
