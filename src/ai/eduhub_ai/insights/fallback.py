"""
Template texts built only from the evidence pack (grounded by construction). Used when AI_ENABLE_LLM=0, when
the LLM fails, or when grounding rejects its answer; also fills explanations or a summary the LLM got wrong.
"""
from dataclasses import dataclass, field
from eduhub_ai.context import GOAL_LABELS, mentions_avoided, wants_conversion
from eduhub_ai.insights.evidence import EvidenceItem, EvidencePack, PostEvidence
from eduhub_shared.models import Evidence, Impact, Insight, InsightCategory, Recommendation

MAX_INSIGHTS = 6
MAX_RECOMMENDATIONS = 6
DEFAULT_CONFIDENCE = 0.5

@dataclass
class WrittenTexts:
    """
    The report texts: insights, recommendations, explanations by post id and summary, plus where they came from.
    """
    insights: list[Insight]
    recommendations: list[Recommendation]
    explanations: dict[str, str]
    summary: str
    source: str = "template"
    errors: list[str] = field(default_factory=list)

def template_texts(pack: EvidencePack, errors: list[str] | None = None) -> WrittenTexts:
    """
    Write every report text from templates over the significant findings (or the best slot if there are none).
    """
    allowed = [item for item in pack.findings if not mentions_avoided(item.label, pack.context)]
    items = diverse(allowed)[:MAX_INSIGHTS] or pack.best_slots[:1]
    insights = [template_insight(item, n) for n, item in enumerate(items, start=1)]
    recommendations = [template_recommendation(item, insight, n, pack)
                       for n, (item, insight) in enumerate(zip(items, insights, strict=True), start=1)]
    return WrittenTexts(
        insights=insights,
        recommendations=recommendations[:MAX_RECOMMENDATIONS],
        explanations=template_explanations(pack),
        summary=template_summary(pack, insights),
        source="template",
        errors=list(errors or []),
    )

def family(item: EvidenceItem) -> str:
    """
    The group an item belongs to for variety: "timing" for every timing dimension, else its dimension.
    """
    return "timing" if item.kind == "timing" else item.id.split(":")[1]

def diverse(findings: list[EvidenceItem]) -> list[EvidenceItem]:
    """
    Keep findings in order, at most one per (family, direction), so templates don't repeat the same idea.
    """
    seen: set[tuple[str, str]] = set()
    kept = []
    for item in findings:
        key = (family(item), item.direction)
        if key not in seen:
            seen.add(key)
            kept.append(item)
    return kept

def impact_for(item: EvidenceItem) -> Impact:
    """
    Impact from how far the segment is from the rest (lift or its inverse).
    """
    lift = item.lift or 1.0
    ratio = max(lift, 1 / lift) if lift > 0 else 2.0
    if ratio >= 1.5:
        return Impact.HIGH
    if ratio >= 1.15:
        return Impact.MEDIUM
    return Impact.LOW

def template_insight(item: EvidenceItem, index: int) -> Insight:
    """
    One insight from one finding or slot.
    """
    mediana = item.numbers.get("mediana", "")
    posts = item.numbers.get("posts", "")
    vs_rest = item.numbers.get("vs_resto", "")
    subject = item.subject[:1].upper() + item.subject[1:]
    if item.kind == "slot":
        title = f"Tu mejor horario: {item.label}"
        description = f"{subject} rinden {mediana} tu post típico ({posts} posts)."
    elif item.direction == "up":
        title = f"{subject} rinden {vs_rest} vs. el resto"
        description = (f"En {posts} posts, {item.subject} rindieron {mediana} tu post típico, "
                       f"{vs_rest} lo que rinden tus demás posts.")
    else:
        title = f"{subject} rinden menos: {vs_rest} vs. el resto"
        description = (f"En {posts} posts, {item.subject} quedaron en {mediana} tu post típico, "
                       f"apenas {vs_rest} de lo que rinden tus demás posts.")
    return Insight(
        id=f"ins-{index}",
        category=item.category,
        title=title,
        description=description,
        evidence=[Evidence(label=item.label, value=item.value)],
        impact=impact_for(item),
        confidence=item.confidence if item.confidence is not None else DEFAULT_CONFIDENCE,
        related_post_ids=item.related_post_ids,
    )

def template_recommendation(item: EvidenceItem, insight: Insight, priority: int, pack: EvidencePack) -> Recommendation:
    """
    One concrete action for an insight. With a selling/traffic/launch brief, a weak link CTA becomes a trade-off.
    """
    if item.id == "seg:cta:link" and item.direction == "down" and wants_conversion(pack.context):
        action = (f"Si necesitás el link, ponelo en una respuesta o en tu bio: en el posteo te cuesta alcance "
                  f"({item.numbers.get('vs_resto', '')} vs. el resto).")
    elif item.kind == "slot":
        action = f"Programá tus próximos posts para los {item.label}."
    elif item.category == InsightCategory.TIMING:
        action = f"Concentrá más {item.short}." if item.direction == "up" else f"Publicá menos {item.short}."
    elif item.direction == "up":
        action = f"Publicá más {item.short}."
    else:
        action = f"Publicá menos {item.short} o cambiales el enfoque."
    return Recommendation(
        id=f"rec-{priority}",
        category=item.category,
        action=action,
        rationale=insight.description,
        priority=priority,
        based_on_insight_ids=[insight.id],
    )

def template_explanation(post: PostEvidence) -> str:
    """
    Why a top or bottom post performed as it did, from its labels.
    """
    reasons = []
    if post.topic:
        reasons.append(f"tema '{post.topic}'")
    reasons.append(f"formato '{post.formato}'")
    reasons.append(f"publicado el {post.dia} a las {post.hora}")
    if post.hook and post.hook != "ninguno":
        reasons.append(f"arranca con {post.hook}")
    if post.rank == "top":
        return f"Rindió {post.score} tu post típico: {', '.join(reasons)}."
    return f"Rindió {post.score} tu post típico, por debajo de lo habitual: {', '.join(reasons)}."

def template_explanations(pack: EvidencePack) -> dict[str, str]:
    """
    Template explanations for every top and bottom post.
    """
    return {p.id: template_explanation(p) for p in [*pack.top_posts, *pack.bottom_posts]}

def template_summary(pack: EvidencePack, insights: list[Insight]) -> str:
    """
    2-4 sentence summary: how many posts, the brief's goal (if any), the engagement rate and the first two insights.
    """
    parts = [f"Analizamos {pack.post_count} posts de @{pack.handle}."]
    if pack.context is not None and pack.context.goal is not None:
        parts.append(f"Tu objetivo: {GOAL_LABELS[pack.context.goal]}.")
    engagement = pack.item("kpi:account:engagement_rate")
    if engagement is not None:
        parts.append(f"Tu engagement promedio es {engagement.value}.")
    parts.extend(f"{insight.title}." for insight in insights[:2])
    return " ".join(parts)
