"""
GET /reports/{report_id} and GET /accounts/{handle}/report.
"""
from typing import Annotated
from fastapi import Depends, FastAPI
from eduhub_backend.api import get_deps
from eduhub_backend.deps import Deps
from eduhub_backend.errors import HttpError
from eduhub_backend.storage import Store
from eduhub_shared.models import AnalysisReport, ErrorCode
from eduhub_shared.models.common import normalize_handle

async def latest_report(store: Store, handle: str) -> AnalysisReport:
    """
    Return the latest report of handle, raising not_found when the handle is invalid or has no report.
    """
    shown = handle.strip().removeprefix("@")
    try:
        report = await store.get_latest_report(normalize_handle(handle))
    except ValueError:
        report = None
    if report is None:
        raise HttpError(ErrorCode.NOT_FOUND, f"Todavía no hay un análisis de @{shown}.")
    return report

async def get_report(report_id: str, deps: Annotated[Deps, Depends(get_deps)]) -> AnalysisReport:
    """
    Get an analysis report.
    """
    report = await deps.store.get_report(report_id)
    if report is None:
        raise HttpError(ErrorCode.NOT_FOUND, "No encontramos ese reporte.")
    return report

async def get_latest_report(handle: str, deps: Annotated[Deps, Depends(get_deps)]) -> AnalysisReport:
    """
    Latest report of an account.
    """
    return await latest_report(deps.store, handle)

def register(app: FastAPI) -> None:
    """
    Add this module's routes to app.
    """
    app.add_api_route(
        "/reports/{report_id}", get_report, methods=["GET"], operation_id="getReport", response_model=AnalysisReport
    )
    app.add_api_route(
        "/accounts/{handle}/report", get_latest_report,
        methods=["GET"], operation_id="getLatestReport", response_model=AnalysisReport
    )
