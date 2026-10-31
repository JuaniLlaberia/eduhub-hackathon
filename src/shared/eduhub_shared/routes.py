"""
Contract C4 route table: the single definition of the HTTP API. openapi.json is generated from it.

Every error response (including request validation errors, status 422) uses the ErrorResponse body.
Disabled optional features answer 501 with code 'feature_disabled'.
"""
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pydantic import BaseModel
from eduhub_shared.models import (
    AnalysisJob,
    AnalysisReport,
    AnalysisRequest,
    DraftRequest,
    DraftsResponse,
    FeatureFlags,
    HealthResponse,
    PublishRequest,
    PublishResult,
    SimulationRequest,
    SimulationResult,
    TrendsResponse,
)

class Priority(StrEnum):
    """
    Product priority of an endpoint.
    """
    MUST = "must"
    WANTED = "wanted"
    STRETCH = "stretch"
    NICE = "nice"

@dataclass(frozen=True)
class Route:
    """
    One HTTP endpoint of the contract.
    """
    method: str
    path: str
    operation_id: str
    summary: str
    priority: Priority
    response_model: type[BaseModel]
    status_code: int = 200
    request_model: type[BaseModel] | None = None
    error_statuses: tuple[int, ...] = field(default=(500,))

    @property
    def path_params(self) -> list[str]:
        """
        Return the names of the path parameters, e.g. ['job_id'].
        """
        return re.findall(r"{(\w+)}", self.path)

ROUTES: tuple[Route, ...] = (
    Route("GET", "/health", "getHealth", "Liveness and contract version", Priority.MUST, HealthResponse),
    Route("GET", "/features", "getFeatures", "Enabled optional features", Priority.MUST, FeatureFlags),
    Route(
        "POST", "/analyses", "createAnalysis", "Start analyzing an account (async job)", Priority.MUST,
        AnalysisJob, status_code=202, request_model=AnalysisRequest, error_statuses=(404, 422, 429, 500, 503),
    ),
    Route(
        "GET", "/analyses/{job_id}", "getAnalysis", "Poll an analysis job", Priority.MUST,
        AnalysisJob, error_statuses=(404, 500),
    ),
    Route(
        "GET", "/reports/{report_id}", "getReport", "Get an analysis report", Priority.MUST,
        AnalysisReport, error_statuses=(404, 500),
    ),
    Route(
        "GET", "/accounts/{handle}/report", "getLatestReport", "Latest report of an account", Priority.MUST,
        AnalysisReport, error_statuses=(404, 500),
    ),
    Route(
        "GET", "/trends", "getTrends", "Current trends in Argentina", Priority.NICE,
        TrendsResponse, error_statuses=(500, 503),
    ),
    Route(
        "POST", "/drafts", "createDrafts", "Generate drafts in the creator's voice", Priority.WANTED,
        DraftsResponse, request_model=DraftRequest, error_statuses=(404, 422, 429, 500, 501),
    ),
    Route(
        "POST", "/publications", "createPublication", "Publish or schedule a post", Priority.WANTED,
        PublishResult, request_model=PublishRequest, error_statuses=(422, 500, 501),
    ),
    Route(
        "POST", "/simulations", "createSimulation", "Test variants with a synthetic audience", Priority.STRETCH,
        SimulationResult, request_model=SimulationRequest, error_statuses=(422, 429, 500, 501),
    ),
)
