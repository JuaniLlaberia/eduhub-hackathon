"""
How the pattern model plugs into the analysis: fit it per account when there is enough data, turn significant
effects into evidence items (pre-formatted es-AR, grounded like everything else), and let effects adjust the
confidence of matching findings. Nothing here is persisted; stage 08 refits from report.posts.
"""
import logging
import time
from eduhub_ai.insights.evidence import (
    CATEGORIES,
    DIMENSION_LABELS,
    RELATED_POSTS,
    VALUE_LABELS,
    EvidenceItem,
    EvidencePack,
    fmt_x,
)
from eduhub_ai.patterns.base import YES, Effect, PatternModel, can_fit, feature_row, level_of
from eduhub_ai.patterns.ridge import RidgePatternModel
from eduhub_shared.models import AnalysisReport, AnalyzedPost, InsightCategory

CONFIDENCE_STEP = 0.1
MIN_EFFECT_SIZE = 0.1
EXTRA_LABELS = {
    "weekend": "Fin de semana", "has_link": "Con link", "is_question": "Con pregunta", "has_emoji": "Con emoji",
    "hashtags": "Hashtags", "matches_trend": "Sobre una tendencia",
}
EXTRA_CATEGORIES = {"weekend": InsightCategory.TIMING, "hashtags": InsightCategory.FORMAT,
                    "matches_trend": InsightCategory.TREND}
logger = logging.getLogger(__name__)

def fit_from_posts(posts: list[AnalyzedPost]) -> PatternModel | None:
    """
    Fit a RidgePatternModel on the scored posts, or return None when can_fit says there is not enough data.
    """
    scored = [p for p in posts if p.score is not None]
    rows = [feature_row(p.features) for p in scored]
    scores = [p.score or 0.0 for p in scored]
    if not can_fit(rows, scores):
        return None
    started = time.perf_counter()
    model = RidgePatternModel()
    model.fit(rows, scores)
    logger.info("pattern model fitted on %d posts in %.2fs", len(rows), time.perf_counter() - started)
    return model

def fit_from_report(report: AnalysisReport) -> PatternModel | None:
    """
    Refit the pattern model from a stored report (its posts carry features and scores).
    """
    return fit_from_posts(report.posts)

def effect_label(effect: Effect) -> str:
    """
    es-AR label of an effect, e.g. "Efecto ajustado: Formato 'foto'" or "Efecto ajustado: Con emoji".
    """
    if effect.value == YES and effect.feature in EXTRA_LABELS:
        return f"Efecto ajustado: {EXTRA_LABELS[effect.feature]}"
    name = DIMENSION_LABELS.get(effect.feature) or EXTRA_LABELS.get(effect.feature, effect.feature)
    return f"Efecto ajustado: {name} '{VALUE_LABELS.get(effect.value, effect.value)}'"

def effect_confidence(effect: Effect) -> float:
    """
    Confidence in 0..1 from the effect's support and how tight its CI is (on a log scale).
    """
    size = min(effect.n, 30) / 30
    width = abs(effect.ci_high - effect.ci_low) / max(effect.multiplier, 0.01)
    return round(min(1.0, 0.2 + 0.5 * size + 0.3 / (1 + width)), 2)

def effect_items(model: PatternModel, posts: list[AnalyzedPost]) -> list[EvidenceItem]:
    """
    Evidence items for the model's significant effects of at least ±10% (smaller ones read as "1,0x" and say
    nothing), with the posts that have each level.
    """
    scored = sorted((p for p in posts if p.score is not None), key=lambda p: (-(p.score or 0), p.post.id))
    rows = {p.post.id: feature_row(p.features) for p in scored}
    items = []
    for effect in model.effects():
        if not effect.significant or abs(effect.multiplier - 1.0) < MIN_EFFECT_SIZE:
            continue
        multiplier = fmt_x(effect.multiplier)
        baseline = VALUE_LABELS.get(effect.baseline, effect.baseline)
        related = [pid for pid, row in rows.items() if level_of(row.get(effect.feature)) == effect.value]
        items.append(EvidenceItem(
            id=f"model:{effect.feature}:{effect.value}",
            kind="pattern",
            category=CATEGORIES.get(effect.feature) or EXTRA_CATEGORIES.get(effect.feature, InsightCategory.OTHER),
            label=effect_label(effect),
            value=f"{multiplier} vs. '{baseline}', a igualdad de lo demás ({effect.n} posts)",
            numbers={"efecto": multiplier, "rango": f"{fmt_x(effect.ci_low)} a {fmt_x(effect.ci_high)}",
                     "posts": str(effect.n)},
            direction="up" if effect.multiplier >= 1 else "down",
            lift=effect.multiplier,
            confidence=effect_confidence(effect),
            related_post_ids=related[:RELATED_POSTS],
        ))
    return items

def adjust_confidence(pack: EvidencePack, model: PatternModel) -> EvidencePack:
    """
    Raise a finding's confidence when the model's effect for the same level agrees (significant, same
    direction), lower it when the effect is not significant or points the other way.
    """
    effects = {(e.feature, e.value): e for e in model.effects()}
    findings = []
    for item in pack.findings:
        _, dimension, value = item.id.split(":", 2)
        effect = effects.get((dimension, value))
        if effect is None or item.confidence is None:
            findings.append(item)
            continue
        agrees = effect.significant and (effect.multiplier >= 1) == (item.direction == "up")
        step = CONFIDENCE_STEP if agrees else -CONFIDENCE_STEP
        confidence = round(min(1.0, max(0.0, item.confidence + step)), 2)
        findings.append(item.model_copy(update={"confidence": confidence}))
    return pack.model_copy(update={"findings": findings})
