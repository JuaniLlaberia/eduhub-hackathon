"""
Insight writer: one LLM call turns the evidence pack into grounded es-AR texts. Insight.evidence, confidence and
ids are built in code; texts with numbers that are not in the evidence are dropped (one retry if most are), and
anything missing falls back to templates. Never raises on LLM failures.
"""
import logging
from pydantic import BaseModel, ConfigDict, Field
from eduhub_ai.config import AISettings
from eduhub_ai.insights.evidence import EvidencePack
from eduhub_ai.insights.fallback import (
    DEFAULT_CONFIDENCE,
    MAX_INSIGHTS,
    MAX_RECOMMENDATIONS,
    WrittenTexts,
    template_explanation,
    template_summary,
    template_texts,
)
from eduhub_ai.insights.grounding import ungrounded
from eduhub_ai.insights.prompts import WRITER_SYSTEM, retry_note, writer_user
from eduhub_ai.llm.client import LLMClient, LLMError
from eduhub_shared.errors import RateLimitedError
from eduhub_shared.models import Evidence, Impact, Insight, InsightCategory, Recommendation

__all__ = ["MAX_INSIGHTS", "MAX_RECOMMENDATIONS", "WriterResponse", "WrittenTexts", "write_texts"]
WRITER_TEMPERATURE = 0.4
MAX_TITLE_CHARS = 90
RELATED_POSTS = 10
LLM_FAILURES = (LLMError, RateLimitedError)
logger = logging.getLogger(__name__)

class InsightDraft(BaseModel):
    """
    An insight as written by the LLM (evidence is referenced by id, never typed).
    """
    model_config = ConfigDict(extra="forbid")
    category: InsightCategory
    title: str
    description: str
    evidence_ids: list[str]
    impact: Impact
    related_post_ids: list[str]

class RecommendationDraft(BaseModel):
    """
    A recommendation as written by the LLM; insight_index are 0-based positions in insights.
    """
    model_config = ConfigDict(extra="forbid")
    category: InsightCategory
    action: str
    rationale: str
    priority: int = Field(ge=1)
    insight_index: list[int]

class ExplanationDraft(BaseModel):
    """
    Why one top/bottom post performed as it did.
    """
    model_config = ConfigDict(extra="forbid")
    post_id: str
    text: str

class WriterResponse(BaseModel):
    """
    The writer's whole answer (lists are capped in code, so a long answer is trimmed instead of rejected).
    """
    model_config = ConfigDict(extra="forbid")
    insights: list[InsightDraft]
    recommendations: list[RecommendationDraft]
    explanations: list[ExplanationDraft]
    summary: str

async def write_texts(pack: EvidencePack, client: LLMClient | None, settings: AISettings) -> WrittenTexts:
    """
    Write the report texts with the LLM, grounded on pack; template texts when disabled or on failure.
    """
    if client is None or not settings.enable_llm:
        return template_texts(pack)
    errors: list[str] = []
    user = writer_user(pack)
    for attempt in range(2):
        try:
            response = await client.complete_json(
                model=settings.writer_model, system=WRITER_SYSTEM, user=user, schema=WriterResponse,
                temperature=WRITER_TEMPERATURE, reasoning=settings.writer_reasoning,
            )
        except LLM_FAILURES as error:
            logger.warning("insight writer failed, using templates: %s", error)
            errors.append(f"writer failed: {error}")
            return template_texts(pack, errors)
        texts, dropped, bad_numbers = assemble(pack, response)
        written = min(len(response.insights), MAX_INSIGHTS)
        if texts.insights and dropped * 2 <= written:
            texts.errors = errors
            return texts
        logger.warning("grounding dropped %d of %d insights (attempt %d)", dropped, written, attempt + 1)
        errors.append(f"grounding dropped {dropped} of {written} insights: {sorted(bad_numbers)}")
        user = writer_user(pack) + retry_note(bad_numbers)
    return template_texts(pack, errors)

def assemble(pack: EvidencePack, response: WriterResponse) -> tuple[WrittenTexts, int, set[str]]:
    """
    Build contract objects from the LLM answer. Returns the texts, how many insights were dropped and the
    ungrounded numbers found.
    """
    bad_numbers: set[str] = set()
    insights: list[Insight] = []
    index_map: dict[int, str] = {}
    for position, draft in enumerate(response.insights[:MAX_INSIGHTS]):
        insight = build_insight(pack, draft, len(insights) + 1, bad_numbers)
        if insight is not None:
            index_map[position] = insight.id
            insights.append(insight)
    dropped = min(len(response.insights), MAX_INSIGHTS) - len(insights)
    texts = WrittenTexts(
        insights=insights,
        recommendations=build_recommendations(pack, response, index_map),
        explanations=build_explanations(pack, response),
        summary=response.summary.strip(),
        source="llm",
    )
    if not texts.summary or ungrounded(texts.summary, pack.allowed_numbers):
        texts.summary = template_summary(pack, insights)
    return texts, dropped, bad_numbers

def build_insight(pack: EvidencePack, draft: InsightDraft, index: int, bad_numbers: set[str]) -> Insight | None:
    """
    An Insight with code-built evidence and confidence, or None if it has ungrounded numbers or no evidence.
    """
    bad = ungrounded(f"{draft.title}\n{draft.description}", pack.allowed_numbers)
    bad_numbers |= bad
    items = [item for item in (pack.item(i) for i in dict.fromkeys(draft.evidence_ids)) if item is not None]
    if bad or not items:
        return None
    related = [pid for pid in dict.fromkeys(draft.related_post_ids) if pid in pack.post_ids]
    if not related:
        related = list(dict.fromkeys(pid for item in items for pid in item.related_post_ids))
    confidences = [item.confidence for item in items if item.confidence is not None]
    return Insight(
        id=f"ins-{index}",
        category=draft.category,
        title=clip(draft.title.strip(), MAX_TITLE_CHARS),
        description=draft.description.strip(),
        evidence=[Evidence(label=item.label, value=item.value) for item in items],
        impact=draft.impact,
        confidence=max(confidences) if confidences else DEFAULT_CONFIDENCE,
        related_post_ids=related[:RELATED_POSTS],
    )

def build_recommendations(
    pack: EvidencePack, response: WriterResponse, index_map: dict[int, str]
) -> list[Recommendation]:
    """
    Grounded recommendations linked to kept insights, ordered by the LLM's priority and renumbered from 1.
    Recommendations that only pointed at dropped insights are dropped too.
    """
    drafts = sorted(response.recommendations[:MAX_RECOMMENDATIONS], key=lambda d: d.priority)
    result: list[Recommendation] = []
    for draft in drafts:
        if ungrounded(f"{draft.action}\n{draft.rationale}", pack.allowed_numbers):
            continue
        links = list(dict.fromkeys(index_map[i] for i in draft.insight_index if i in index_map))
        if draft.insight_index and not links:
            continue
        result.append(Recommendation(
            id=f"rec-{len(result) + 1}",
            category=draft.category,
            action=draft.action.strip(),
            rationale=draft.rationale.strip(),
            priority=len(result) + 1,
            based_on_insight_ids=links,
        ))
    return result

def build_explanations(pack: EvidencePack, response: WriterResponse) -> dict[str, str]:
    """
    One explanation per top/bottom post: the LLM's when grounded, the template's otherwise.
    """
    wanted = [*pack.top_posts, *pack.bottom_posts]
    written = {}
    for draft in response.explanations:
        text = draft.text.strip()
        if text and draft.post_id not in written and not ungrounded(text, pack.allowed_numbers):
            written[draft.post_id] = text
    return {post.id: written.get(post.id) or template_explanation(post) for post in wanted}

def clip(text: str, limit: int) -> str:
    """
    Cut text at a word boundary so it fits in limit characters.
    """
    if len(text) <= limit:
        return text
    return text[:limit - 1].rsplit(" ", 1)[0] + "…"
