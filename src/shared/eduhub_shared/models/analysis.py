from enum import StrEnum
from pydantic import AwareDatetime, Field, NonNegativeFloat, NonNegativeInt
from eduhub_shared.models.account import AccountProfile, MediaType, Post
from eduhub_shared.models.common import ContractModel
from eduhub_shared.models.context import CreatorContext

Rate = NonNegativeFloat

class LengthBucket(StrEnum):
    """
    Post length bucket. Thresholds live in eduhub_shared.metrics.length_bucket.
    """
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"

class SegmentDimension(StrEnum):
    """
    Dimension used to group posts in segment stats.
    """
    TOPIC = "topic"
    MEDIA_TYPE = "media_type"
    LENGTH_BUCKET = "length_bucket"
    TONE = "tone"
    POST_KIND = "post_kind"
    HOOK = "hook"
    CTA = "cta"

class InsightCategory(StrEnum):
    """
    What an insight or recommendation is about.
    """
    TIMING = "timing"
    TOPIC = "topic"
    FORMAT = "format"
    LENGTH = "length"
    TONE = "tone"
    TREND = "trend"
    HOOK = "hook"
    CTA = "cta"
    OTHER = "other"

class Impact(StrEnum):
    """
    Estimated impact of acting on an insight.
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class PostRates(ContractModel):
    """
    Rates of a post over impressions (see eduhub_shared.metrics). None when impressions are missing or zero.
    """
    engagement_rate: Rate | None
    save_rate: Rate | None
    share_rate: Rate | None
    reply_rate: Rate | None
    like_rate: Rate | None
    passive_rate: Rate | None

class PostFeatures(ContractModel):
    """
    Features extracted from a post. Semantic fields (topic, tone, sentiment, hook, cta) may be None.
    """
    char_count: NonNegativeInt
    word_count: NonNegativeInt
    length_bucket: LengthBucket
    hour_local: int = Field(ge=0, le=23, description="Hour in America/Argentina/Buenos_Aires.")
    weekday: int = Field(ge=0, le=6, description="0 = Monday … 6 = Sunday, Argentina time.")
    media_type: MediaType | None = Field(description="First media item; None = text only.")
    has_link: bool
    hashtag_count: NonNegativeInt
    mention_count: NonNegativeInt
    is_question: bool
    has_emoji: bool
    topic: str | None = None
    tone: str | None = None
    sentiment: float | None = Field(default=None, ge=-1, le=1)
    hook: str | None = Field(default=None, description="How the post opens (label set defined by eduhub_ai).")
    cta: str | None = Field(default=None, description="What the post asks the reader to do (label set by eduhub_ai).")
    matches_trend: bool | None = None

class AnalyzedPost(ContractModel):
    """
    A post with its features, rates, relative score and optional explanation.
    """
    post: Post
    features: PostFeatures
    rates: PostRates
    score: NonNegativeFloat | None = Field(description="Performance vs the account's typical post (1.0 = typical).")
    explanation: str | None = Field(default=None, description="es-AR: why it performed so (at least top/bottom posts).")

class AccountKPIs(ContractModel):
    """
    Account-level KPIs. Rates are aggregated as sum(interactions) / sum(impressions).
    """
    post_count: NonNegativeInt
    period_start: AwareDatetime | None
    period_end: AwareDatetime | None
    posts_per_week: NonNegativeFloat
    avg_impressions: NonNegativeFloat | None
    median_impressions: NonNegativeFloat | None
    rates: PostRates

class TimeSlotStat(ContractModel):
    """
    Performance of posts published in a weekday/hour slot (Argentina time).
    """
    weekday: int = Field(ge=0, le=6)
    hour: int = Field(ge=0, le=23)
    post_count: NonNegativeInt
    avg_score: NonNegativeFloat | None

class SegmentStat(ContractModel):
    """
    Performance of posts sharing a value of one dimension (e.g. topic = "ahorro").
    """
    dimension: SegmentDimension
    value: str
    post_count: NonNegativeInt
    avg_score: NonNegativeFloat | None
    engagement_rate: Rate | None

class Evidence(ContractModel):
    """
    A displayable data point backing an insight, e.g. label "Tasa de guardados", value "2,1% vs 0,8%".
    """
    label: str
    value: str

class Insight(ContractModel):
    """
    A pattern found in the account's data, explained in es-AR.
    """
    id: str
    category: InsightCategory
    title: str
    description: str
    evidence: list[Evidence] = Field(default_factory=list)
    impact: Impact
    confidence: float = Field(ge=0, le=1)
    related_post_ids: list[str] = Field(default_factory=list)

class Recommendation(ContractModel):
    """
    A concrete action for the creator, in es-AR. Priority 1 is the most important.
    """
    id: str
    category: InsightCategory
    action: str
    rationale: str
    priority: int = Field(ge=1)
    based_on_insight_ids: list[str] = Field(default_factory=list)

class AnalysisReport(ContractModel):
    """
    Full analysis of an account. This is the AI output contract and the dashboard's data.
    """
    id: str
    profile: AccountProfile
    generated_at: AwareDatetime
    kpis: AccountKPIs
    posts: list[AnalyzedPost] = Field(description="Every snapshot post exactly once, newest first.")
    heatmap: list[TimeSlotStat] = Field(description="Only slots with at least one post.")
    segments: list[SegmentStat]
    best_time_slots: list[TimeSlotStat] = Field(max_length=5)
    insights: list[Insight]
    recommendations: list[Recommendation]
    summary: str = Field(description="es-AR, 2-4 sentences.")
    engine: str = Field(description="Which analyzer produced it, e.g. 'fake' or 'hybrid-v1'.")
    context: CreatorContext | None = Field(default=None, description="The creator brief the report was made with.")
