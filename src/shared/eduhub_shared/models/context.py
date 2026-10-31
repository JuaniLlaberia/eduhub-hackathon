from enum import StrEnum
from typing import Annotated
from pydantic import ConfigDict, Field
from eduhub_shared.models.audience import AudienceFilters
from eduhub_shared.models.common import ContractModel

class CreatorGoal(StrEnum):
    """
    What the creator publishes for. es-AR labels live in the frontend.
    """
    SELL = "sell"
    TRAFFIC = "traffic"
    REACH = "reach"
    COMMUNITY = "community"
    LAUNCH = "launch"
    OTHER = "other"

class PreferredCta(StrEnum):
    """
    What the creator wants readers to do.
    """
    LINK = "link"
    REPLY = "reply"
    SAVE = "save"
    SHARE = "share"
    FOLLOW = "follow"
    NONE = "none"

AvoidTopic = Annotated[str, Field(max_length=60)]

class CreatorContext(ContractModel):
    """
    The creator's brief ("el para qué"): goal, offering, audience, voice. Every field is optional, free text is
    es-AR. The AI uses it to frame and prioritize; it never changes computed numbers.
    It travels in requests and responses, so it keeps one OpenAPI schema (no -Input/-Output split).
    """
    model_config = ConfigDict(json_schema_serialization_defaults_required=False)
    goal: CreatorGoal | None = None
    goal_detail: str | None = Field(default=None, max_length=300)
    offering: str | None = Field(default=None, max_length=500, description="Product, service or campaign.")
    target_audience: str | None = Field(default=None, max_length=300)
    audience_filters: AudienceFilters = Field(default_factory=AudienceFilters)
    brand_voice: str | None = Field(default=None, max_length=300)
    avoid_topics: list[AvoidTopic] = Field(default_factory=list, max_length=10)
    preferred_cta: PreferredCta | None = None
