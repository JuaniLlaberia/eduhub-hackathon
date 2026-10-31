from pydantic import AwareDatetime, Field, NonNegativeFloat
from eduhub_shared.models.common import ContractModel, Handle

class DraftRequest(ContractModel):
    """
    Ask for drafts for an already analyzed account, optionally based on a topic or a recommendation.
    """
    handle: Handle
    topic: str | None = None
    recommendation_id: str | None = None
    instructions: str | None = Field(default=None, max_length=500)
    count: int = Field(default=3, ge=1, le=5)

class Draft(ContractModel):
    """
    A generated post draft in the creator's voice (es-AR).
    """
    id: str
    text: str = Field(min_length=1, max_length=4000)
    rationale: str
    suggested_time: AwareDatetime | None = None
    estimated_score: NonNegativeFloat | None = Field(default=None, description="Same scale as AnalyzedPost.score.")
    based_on_insight_ids: list[str] = Field(default_factory=list)
