from enum import StrEnum
from pydantic import AwareDatetime, Field
from eduhub_shared.models.common import ContractModel, Handle

class PublishStatus(StrEnum):
    """
    Outcome of a publish request. INTENT means the user must confirm in X via the returned compose URL.
    """
    PUBLISHED = "published"
    SCHEDULED = "scheduled"
    INTENT = "intent"
    FAILED = "failed"

class PublishRequest(ContractModel):
    """
    Publish a text now, or schedule it when scheduled_for is set.
    """
    handle: Handle
    text: str = Field(min_length=1, max_length=4000)
    scheduled_for: AwareDatetime | None = None

class PublishResult(ContractModel):
    """
    Result of a publish request.
    """
    status: PublishStatus
    post_id: str | None = None
    url: str | None = Field(default=None, description="Published post URL, or compose URL when status is 'intent'.")
    scheduled_for: AwareDatetime | None = None
    error: str | None = None
