"""
POST /publications.
"""
from typing import Annotated
from fastapi import Depends, FastAPI
from eduhub_backend.api import get_deps
from eduhub_backend.deps import Deps
from eduhub_shared.models import PublishRequest, PublishResult

async def create_publication(request: PublishRequest, deps: Annotated[Deps, Depends(get_deps)]) -> PublishResult:
    """
    Publish or schedule a post.
    """
    return await deps.publisher.publish(request)

def register(app: FastAPI) -> None:
    """
    Add this module's routes to app.
    """
    app.add_api_route(
        "/publications", create_publication,
        methods=["POST"], operation_id="createPublication", response_model=PublishResult
    )
