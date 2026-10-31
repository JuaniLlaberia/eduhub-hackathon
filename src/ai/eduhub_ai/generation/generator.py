"""
LLMDraftGenerator: drafts in the creator's voice from the stored report (voice examples = top posts), the
selected recommendation, the topic and current trends. Each draft gets a suggested time on one of the best
slots and an estimated score from the account's own pattern model ("lo genera la IA y lo evalúa tu modelo").
"""
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo
from eduhub_ai.config import AISettings
from eduhub_ai.features.deterministic import extract_deterministic
from eduhub_ai.generation.prompts import GENERATOR_SYSTEM, generator_user, retry_note
from eduhub_ai.generation.schemas import DraftItem, DraftsResponse
from eduhub_ai.labeling.schemas import OTHER_TOPIC
from eduhub_ai.llm.client import LLMClient, LLMError
from eduhub_ai.patterns import feature_row, fit_from_report
from eduhub_shared.errors import GenerationError
from eduhub_shared.models import (
    AnalysisReport,
    Draft,
    DraftRequest,
    Insight,
    MediaType,
    Post,
    PostFeatures,
    PostMetrics,
    Recommendation,
    SegmentDimension,
    SegmentStat,
    Trend,
)

type Scorer = Callable[[PostFeatures], float | None]
AR_TZ = ZoneInfo("America/Argentina/Buenos_Aires")
DRAFT_NAMESPACE = uuid.UUID("4d7a2c19-8b3e-4f60-a1d5-9e0c6b2f8a73")
VOICE_EXAMPLES = 6
MAX_TRENDS = 3
MAX_DRAFT_CHARS = 4000
MIN_TOPIC_POSTS = 3
GENERATOR_TEMPERATURE = 0.8
FAILED = "No pudimos generar borradores. Probá de nuevo en unos minutos."
TOO_FEW = "No pudimos generar suficientes borradores distintos. Probá de nuevo o cambiá el pedido."
logger = logging.getLogger(__name__)

def utc_now() -> datetime:
    """
    The current time in UTC.
    """
    return datetime.now(UTC)

def next_slot_after(moment: datetime, weekday: int, hour: int) -> datetime:
    """
    The next datetime (UTC) after moment that falls on weekday/hour in Argentina time.
    """
    local = moment.astimezone(AR_TZ).replace(minute=0, second=0, microsecond=0)
    candidate = (local + timedelta(days=(weekday - local.weekday()) % 7)).replace(hour=hour)
    if candidate <= moment:
        candidate += timedelta(days=7)
    return candidate.astimezone(UTC)

class LLMDraftGenerator:
    """
    DraftGenerator backed by the LLM. scorer=None builds the default scorer from each report.
    """
    def __init__(
        self,
        settings: AISettings,
        client: LLMClient,
        clock: Callable[[], datetime] = utc_now,
        scorer: Scorer | None = None,
    ) -> None:
        """
        Keep the settings, the LLM client, the clock (for suggested times) and an optional fixed scorer.
        """
        self.settings = settings
        self.client = client
        self._clock = clock
        self._scorer = scorer

    async def generate(self, request: DraftRequest, report: AnalysisReport, trends: list[Trend]) -> list[Draft]:
        """
        Return request.count drafts. Raises GenerationError (es-AR) on LLM failure or too few distinct drafts;
        RateLimitedError propagates for the backend's 429.
        """
        recommendation = pick_recommendation(report, request.recommendation_id)
        insights = based_on(report, recommendation)
        payload = build_payload(request, report, trends, recommendation, insights)
        items = await self._collect(payload, request.count)
        now = self._clock()
        scorer = self._scorer or default_scorer(report)
        slots = report.best_time_slots
        drafts = []
        for index, item in enumerate(items):
            slot = slots[index % len(slots)] if slots else None
            suggested = next_slot_after(now, slot.weekday, slot.hour) if slot else None
            drafts.append(Draft(
                id=str(uuid.uuid5(DRAFT_NAMESPACE, f"{report.id}|{now.isoformat()}|{index}|{item.text}")),
                text=item.text[:MAX_DRAFT_CHARS],
                rationale=item.rationale.strip(),
                suggested_time=suggested,
                estimated_score=safe_score(scorer, draft_features(item, report, suggested or now)),
                based_on_insight_ids=[i.id for i in insights],
            ))
        return drafts

    async def _collect(self, payload: dict[str, Any], count: int) -> list[DraftItem]:
        """
        Ask for count drafts, dedupe them, and retry once for the missing ones.
        """
        items = dedupe(await self._ask(generator_user(payload)))
        if len(items) < count:
            missing = {**payload, "cantidad": count - len(items)}
            user = generator_user(missing) + retry_note([i.text for i in items])
            items = dedupe([*items, *await self._ask(user)])
        if len(items) < count:
            raise GenerationError(TOO_FEW)
        return items[:count]

    async def _ask(self, user: str) -> list[DraftItem]:
        """
        One LLM call; LLM failures become GenerationError (rate limits pass through).
        """
        try:
            response = await self.client.complete_json(
                model=self.settings.writer_model, system=GENERATOR_SYSTEM, user=user, schema=DraftsResponse,
                temperature=GENERATOR_TEMPERATURE, reasoning=self.settings.writer_reasoning,
            )
        except LLMError as error:
            logger.warning("draft generation failed: %s", error)
            raise GenerationError(FAILED) from error
        return response.drafts

def dedupe(items: list[DraftItem]) -> list[DraftItem]:
    """
    Drop empty drafts and repeats (case- and whitespace-insensitive), keeping the first of each.
    """
    seen: set[str] = set()
    kept = []
    for item in items:
        key = " ".join(item.text.casefold().split())
        if key and key not in seen:
            seen.add(key)
            kept.append(item.model_copy(update={"text": item.text.strip()}))
    return kept

def pick_recommendation(report: AnalysisReport, recommendation_id: str | None) -> Recommendation | None:
    """
    The requested recommendation, or the top-priority one when the id is missing or unknown.
    """
    by_id = {r.id: r for r in report.recommendations}
    if recommendation_id in by_id:
        return by_id[recommendation_id]
    return min(report.recommendations, key=lambda r: r.priority, default=None)

def based_on(report: AnalysisReport, recommendation: Recommendation | None) -> list[Insight]:
    """
    The insights behind the recommendation, or the top two insights.
    """
    by_id = {i.id: i for i in report.insights}
    if recommendation is not None:
        linked = [by_id[i] for i in recommendation.based_on_insight_ids if i in by_id]
        if linked:
            return linked
    return report.insights[:2]

def topic_segments(report: AnalysisReport) -> list[SegmentStat]:
    """
    Topic segments with a score, best first (callers filter by post count where it matters).
    """
    segments = [s for s in report.segments if s.dimension == SegmentDimension.TOPIC and s.avg_score is not None]
    return sorted(segments, key=lambda s: (-(s.avg_score or 0), s.value))

def best_values(report: AnalysisReport, dimension: SegmentDimension) -> list[str]:
    """
    Values of a dimension that beat the typical post with at least MIN_TOPIC_POSTS posts, best first.
    """
    segments = [s for s in report.segments if s.dimension == dimension and s.post_count >= MIN_TOPIC_POSTS
                and (s.avg_score or 0) > 1]
    return [s.value for s in sorted(segments, key=lambda s: -(s.avg_score or 0))]

def voice_examples(report: AnalysisReport) -> list[str]:
    """
    Texts of the best-scoring posts, the creator's voice to imitate.
    """
    scored = sorted((p for p in report.posts if p.score is not None), key=lambda p: (-(p.score or 0), p.post.id))
    return [p.post.text for p in scored[:VOICE_EXAMPLES]]

def top_trends(trends: list[Trend]) -> list[str]:
    """
    Up to MAX_TRENDS trend names, by rank.
    """
    ranked = sorted(trends, key=lambda t: (t.rank is None, t.rank or 0, t.name))
    return [t.name for t in ranked[:MAX_TRENDS]]

def build_payload(
    request: DraftRequest,
    report: AnalysisReport,
    trends: list[Trend],
    recommendation: Recommendation | None,
    insights: list[Insight],
) -> dict[str, Any]:
    """
    Everything the LLM needs, as a JSON-ready dict.
    """
    topics = topic_segments(report)
    reliable = [s for s in topics if s.post_count >= MIN_TOPIC_POSTS]
    objective: dict[str, Any] = {"insights": [{"titulo": i.title, "detalle": i.description} for i in insights]}
    if recommendation is not None:
        objective["recomendacion"] = {"accion": recommendation.action, "por_que": recommendation.rationale}
    return {
        "cuenta": f"@{report.profile.handle}",
        "ejemplos": voice_examples(report),
        "objetivo": objective,
        "tema": request.topic or (reliable[0].value if reliable else None),
        "temas_de_la_cuenta": [s.value for s in topics],
        "mejores_ganchos": best_values(report, SegmentDimension.HOOK),
        "mejores_cta": best_values(report, SegmentDimension.CTA),
        "tendencias": top_trends(trends),
        "instrucciones": request.instructions,
        "cantidad": request.count,
    }

def draft_features(item: DraftItem, report: AnalysisReport, when: datetime) -> PostFeatures:
    """
    Features of a draft as if it were posted at when with its intended media: deterministic ones from its text
    plus its LLM labels.
    """
    known_topics = {s.value for s in topic_segments(report)}
    post = Post(
        id="draft",
        author_handle=report.profile.handle,
        text=item.text,
        created_at=when,
        url="https://x.com/draft",
        media=[] if item.media == "text" else [MediaType(item.media)],
        metrics=PostMetrics(impressions=None, likes=0, reposts=0, quotes=0, replies=0, bookmarks=0),
    )
    topic = item.topic if item.topic in known_topics else None
    return extract_deterministic(post, []).model_copy(
        update={"topic": topic, "tone": item.tone, "hook": item.hook, "cta": item.cta})

def default_scorer(report: AnalysisReport) -> Scorer:
    """
    The account's pattern model when it can be refit from the report, else the median score of the draft's
    topic segment (None for unknown topics).
    """
    model = fit_from_report(report)
    if model is not None:
        return lambda features: model.predict(feature_row(features))
    by_topic = {s.value: s.avg_score for s in topic_segments(report) if s.value != OTHER_TOPIC}
    return lambda features: by_topic.get(features.topic) if features.topic else None

def safe_score(scorer: Scorer, features: PostFeatures) -> float | None:
    """
    Run the scorer; a failure or a negative value means no estimate rather than a failed generation.
    """
    try:
        score = scorer(features)
    except (ValueError, ArithmeticError, RuntimeError) as error:
        logger.warning("draft scoring failed: %s", error)
        return None
    return score if score is not None and score >= 0 else None
