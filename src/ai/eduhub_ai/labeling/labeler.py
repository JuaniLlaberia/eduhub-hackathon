"""
Semantic labeling: (1) a per-account topic taxonomy from a sample, (2) topic, tone, sentiment, hook and CTA for
every post in concurrent batches. LLM failures never raise here: affected posts keep None labels.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from eduhub_ai.config import AISettings
from eduhub_ai.labeling import prompts
from eduhub_ai.labeling.schemas import MAX_TOPICS, OTHER_TOPIC, PostLabel, TaxonomyResponse, label_batch_schema
from eduhub_ai.llm.client import LLMClient, LLMError
from eduhub_shared.errors import RateLimitedError
from eduhub_shared.models import CreatorContext, Post, PostFeatures

TAXONOMY_SAMPLE_SIZE = 60
DEFAULT_BATCH_SIZE = 25
LABEL_TEMPERATURE = 0.0
TAXONOMY_TEMPERATURE = 0.2
LLM_FAILURES = (LLMError, RateLimitedError)
logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class LabelingResult:
    """
    Features with labels merged in, the taxonomy used ([] if none), the share of posts labeled, and errors.
    """
    features: dict[str, PostFeatures]
    taxonomy: list[str] = field(default_factory=list)
    coverage: float = 0.0
    errors: list[str] = field(default_factory=list)

def sample_for_taxonomy(posts: list[Post], limit: int = TAXONOMY_SAMPLE_SIZE) -> list[Post]:
    """
    Pick up to limit posts evenly spaced by date (oldest first), independent of input order.
    """
    ordered = sorted(posts, key=lambda p: (p.created_at, p.id))
    if len(ordered) <= limit:
        return ordered
    step = (len(ordered) - 1) / (limit - 1)
    return [ordered[round(i * step)] for i in range(limit)]

def normalize_taxonomy(topics: list[str]) -> list[str]:
    """
    Lowercase, trim and collapse spaces, drop duplicates and "otros", cap at MAX_TOPICS, then append "otros".
    """
    seen: list[str] = []
    for topic in topics:
        label = " ".join(topic.casefold().split())
        if label and label != OTHER_TOPIC and label not in seen:
            seen.append(label)
    return [*seen[:MAX_TOPICS], OTHER_TOPIC]

async def build_taxonomy(
    posts: list[Post], client: LLMClient, settings: AISettings, context: CreatorContext | None = None
) -> list[str]:
    """
    Ask the LLM for this account's topics from a sample of posts (the brief's offering is a naming hint).
    Raises LLMError/RateLimitedError on failure.
    """
    sample = sample_for_taxonomy(posts)
    response = await client.complete_json(
        model=settings.label_model,
        system=prompts.TAXONOMY_SYSTEM,
        user=prompts.taxonomy_user(sample, context),
        schema=TaxonomyResponse,
        temperature=TAXONOMY_TEMPERATURE,
        reasoning=settings.label_reasoning,
    )
    return normalize_taxonomy(response.topics)

async def label_posts(
    posts: list[Post],
    taxonomy: list[str],
    client: LLMClient,
    settings: AISettings,
    batch_size: int = DEFAULT_BATCH_SIZE,
    errors: list[str] | None = None,
) -> dict[str, PostLabel]:
    """
    Label posts in concurrent batches (the client limits concurrency). Unknown ids in a response are ignored;
    posts still unlabeled after one retry of their batch get no label. Failures are appended to errors.
    """
    errors = [] if errors is None else errors
    batches = [posts[i:i + batch_size] for i in range(0, len(posts), batch_size)]
    results = await asyncio.gather(*[_label_batch(b, taxonomy, client, settings, errors) for b in batches])
    return {post_id: label for batch in results for post_id, label in batch.items()}

async def _label_batch(
    batch: list[Post], taxonomy: list[str], client: LLMClient, settings: AISettings, errors: list[str]
) -> dict[str, PostLabel]:
    """
    Label one batch, then retry once with the posts that came back missing (or all of them, if the call failed).
    """
    labels: dict[str, PostLabel] = {}
    pending = batch
    for attempt in range(2):
        try:
            labels |= await _request_labels(pending, taxonomy, client, settings)
        except LLM_FAILURES as error:
            logger.warning("label batch failed (attempt %d, %d posts): %s", attempt + 1, len(pending), error)
            if attempt == 1:
                errors.append(f"labeling failed for {len(pending)} posts: {error}")
        pending = [p for p in pending if p.id not in labels]
        if not pending:
            break
    return labels

async def _request_labels(
    batch: list[Post], taxonomy: list[str], client: LLMClient, settings: AISettings
) -> dict[str, PostLabel]:
    """
    One labeling call; keep only the first label of each id that belongs to the batch.
    """
    response = await client.complete_json(
        model=settings.label_model,
        system=prompts.LABEL_SYSTEM,
        user=prompts.label_user(batch, taxonomy),
        schema=label_batch_schema(taxonomy),
        temperature=LABEL_TEMPERATURE,
        reasoning=settings.label_reasoning,
    )
    wanted = {p.id for p in batch}
    labels: dict[str, PostLabel] = {}
    for label in response.labels:
        if label.post_id in wanted and label.post_id not in labels:
            labels[label.post_id] = label
    return labels

def apply_labels(features: dict[str, PostFeatures], labels: dict[str, PostLabel]) -> dict[str, PostFeatures]:
    """
    Return a copy of features with each post's labels merged in; posts without a label are unchanged.
    """
    merged = dict(features)
    for post_id, label in labels.items():
        if post_id in merged:
            update = {"topic": label.topic, "tone": label.tone, "sentiment": label.sentiment,
                      "hook": label.hook, "cta": label.cta}
            merged[post_id] = merged[post_id].model_copy(update=update)
    return merged

def hashtag_topics(posts: list[Post], features: dict[str, PostFeatures]) -> dict[str, PostFeatures]:
    """
    Fallback topic when there is no taxonomy: the first hashtag, lowercased (None without hashtags).
    """
    merged = dict(features)
    for post in posts:
        if post.id in merged:
            topic = post.hashtags[0].casefold() if post.hashtags else None
            merged[post.id] = merged[post.id].model_copy(update={"topic": topic})
    return merged

async def label_account(
    posts: list[Post],
    features: dict[str, PostFeatures],
    client: LLMClient | None,
    settings: AISettings,
    batch_size: int = DEFAULT_BATCH_SIZE,
    context: CreatorContext | None = None,
) -> LabelingResult:
    """
    Run both passes and merge the labels into features. Never raises on LLM failures: without a client (or with
    AI_ENABLE_LLM=0) it makes no calls; if the taxonomy fails, topics fall back to hashtags and style labels
    (tone, sentiment, hook, cta) still run.
    """
    if client is None or not settings.enable_llm or not posts:
        return LabelingResult(features=dict(features))
    errors: list[str] = []
    try:
        taxonomy = await build_taxonomy(posts, client, settings, context)
    except LLM_FAILURES as error:
        logger.warning("taxonomy failed, falling back to hashtag topics: %s", error)
        errors.append(f"taxonomy failed: {error}")
        taxonomy = []
    labels = await label_posts(posts, taxonomy or [OTHER_TOPIC], client, settings, batch_size, errors)
    merged = apply_labels(features, labels)
    if not taxonomy:
        merged = hashtag_topics(posts, merged)
    return LabelingResult(features=merged, taxonomy=taxonomy, coverage=len(labels) / len(posts), errors=errors)
