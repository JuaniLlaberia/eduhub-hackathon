from enum import StrEnum
from typing import Literal
from pydantic import AwareDatetime, Field
from eduhub_shared.models.account import Trend
from eduhub_shared.models.common import ContractModel, Handle
from eduhub_shared.models.context import CreatorContext
from eduhub_shared.models.generation import Draft

class ErrorCode(StrEnum):
    """
    Machine-readable error codes returned by the HTTP API.
    """
    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
    ACCOUNT_NOT_FOUND = "account_not_found"
    SOURCE_UNAVAILABLE = "source_unavailable"
    RATE_LIMITED = "rate_limited"
    ANALYSIS_FAILED = "analysis_failed"
    GENERATION_FAILED = "generation_failed"
    SIMULATION_FAILED = "simulation_failed"
    FEATURE_DISABLED = "feature_disabled"
    INTERNAL_ERROR = "internal_error"

class ApiError(ContractModel):
    """
    Error details. message is human readable (es-AR) and safe to show in the UI.
    """
    code: ErrorCode
    message: str

class ErrorResponse(ContractModel):
    """
    Body of every non-2xx response.
    """
    error: ApiError

class HealthResponse(ContractModel):
    """
    Liveness response, including the contract version the backend implements.
    """
    status: Literal["ok"] = "ok"
    contract_version: str

class FeatureFlags(ContractModel):
    """
    Which optional features are enabled. The frontend hides disabled ones.
    """
    generation: bool
    publishing: bool
    simulation: bool
    demo_mode: bool

class AnalysisRequest(ContractModel):
    """
    Start analyzing an account.
    """
    handle: Handle
    max_posts: int = Field(default=200, ge=10, le=500)
    context: CreatorContext | None = Field(default=None, description="Optional creator brief (\"el para qué\").")

class JobStatus(StrEnum):
    """
    Lifecycle of an analysis job: queued -> fetching -> analyzing -> done | failed.
    """
    QUEUED = "queued"
    FETCHING = "fetching"
    ANALYZING = "analyzing"
    DONE = "done"
    FAILED = "failed"

class AnalysisJob(ContractModel):
    """
    Status of an analysis job. report_id is set when status is 'done'; error when 'failed'.
    """
    id: str
    handle: Handle
    status: JobStatus
    progress: float = Field(ge=0, le=1)
    message: str | None = Field(default=None, description="es-AR label of the current step.")
    created_at: AwareDatetime
    updated_at: AwareDatetime
    report_id: str | None = None
    error: ApiError | None = None

class DraftsResponse(ContractModel):
    """
    Drafts generated for a request.
    """
    drafts: list[Draft]

class TrendsResponse(ContractModel):
    """
    Current trends.
    """
    trends: list[Trend]
