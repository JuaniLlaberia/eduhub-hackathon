from enum import StrEnum
from pydantic import Field, NonNegativeInt, PositiveFloat
from eduhub_shared.models.analysis import Rate
from eduhub_shared.models.audience import AudienceFilters
from eduhub_shared.models.common import ContractModel, Handle
from eduhub_shared.models.context import CreatorContext

class ReactionType(StrEnum):
    """
    What a simulated persona does with a post. IGNORE and READ are passive.
    """
    IGNORE = "ignore"
    READ = "read"
    LIKE = "like"
    REPLY = "reply"
    REPOST = "repost"
    BOOKMARK = "bookmark"

class AudienceDimension(StrEnum):
    """
    Persona attribute used to break down simulation results.
    """
    AGE_GROUP = "age_group"
    GENDER = "gender"
    PROVINCE = "province"
    SOCIOECONOMIC_LEVEL = "socioeconomic_level"

class Persona(ContractModel):
    """
    A synthetic audience member, sampled from real survey respondents (ENCC 2022-23 via OpenARG).
    """
    id: str
    age_group: str
    gender: str
    province: str
    socioeconomic_level: str | None = None
    platforms: list[str] = Field(default_factory=list)
    traits: list[str] = Field(default_factory=list, description="Short es-AR descriptors.")
    weight: PositiveFloat = Field(description="Survey expansion weight.")

class SimulationRequest(ContractModel):
    """
    Test 1-3 text variants against a synthetic audience.
    """
    handle: Handle | None = None
    variants: list[str] = Field(min_length=1, max_length=3)
    audience_size: int = Field(default=50, ge=5, le=200)
    filters: AudienceFilters = Field(default_factory=AudienceFilters)
    context: CreatorContext | None = Field(default=None, description="Optional creator brief (product, audience).")

class PersonaReaction(ContractModel):
    """
    One persona's reaction to one variant.
    """
    persona_id: str
    variant_index: NonNegativeInt
    reaction: ReactionType
    comment: str | None = None
    sentiment: float | None = Field(default=None, ge=-1, le=1)

class VariantResult(ContractModel):
    """
    Aggregated reactions to one variant. interaction_rate = weighted share of active reactions.
    """
    variant_index: NonNegativeInt
    text: str
    interaction_rate: Rate
    reaction_counts: dict[ReactionType, NonNegativeInt]

class SegmentReaction(ContractModel):
    """
    Interaction rate of one audience segment for one variant.
    """
    dimension: AudienceDimension
    value: str
    variant_index: NonNegativeInt
    persona_count: NonNegativeInt
    interaction_rate: Rate

class SimulationResult(ContractModel):
    """
    Result of a simulation. Orientative only: it compares variants, it does not predict real engagement.
    """
    id: str
    personas: list[Persona]
    reactions: list[PersonaReaction]
    variants: list[VariantResult]
    segments: list[SegmentReaction]
    best_variant_index: NonNegativeInt
    summary: str
    disclaimer: str
