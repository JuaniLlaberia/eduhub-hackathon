"""
POST /analyses and GET /analyses/{job_id}.
"""
from typing import Annotated
from fastapi import Depends, FastAPI
from eduhub_backend.api import get_deps, get_runner
from eduhub_backend.deps import Deps
from eduhub_backend.errors import HttpError
from eduhub_backend.jobs import JobRunner
from eduhub_shared.models import AnalysisJob, AnalysisRequest, ErrorCode

async def create_analysis(
    request: AnalysisRequest,
    deps: Annotated[Deps, Depends(get_deps)],
    runner: Annotated[JobRunner, Depends(get_runner)],
) -> AnalysisJob:
    """
    Check the account exists, then start analyzing it in the background.
    """
    profile = await deps.source.fetch_profile(request.handle)
    return await runner.start(request, profile)

async def get_analysis(job_id: str, deps: Annotated[Deps, Depends(get_deps)]) -> AnalysisJob:
    """
    Poll an analysis job.
    """
    job = await deps.store.get_job(job_id)
    if job is None:
        raise HttpError(ErrorCode.NOT_FOUND, "No encontramos ese análisis.")
    return job

def register(app: FastAPI) -> None:
    """
    Add this module's routes to app.
    """
    app.add_api_route(
        "/analyses", create_analysis,
        methods=["POST"], operation_id="createAnalysis", response_model=AnalysisJob, status_code=202
    )
    app.add_api_route(
        "/analyses/{job_id}", get_analysis, methods=["GET"], operation_id="getAnalysis", response_model=AnalysisJob
    )
