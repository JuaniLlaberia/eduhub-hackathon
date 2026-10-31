"""
The creator brief ("el para qué", contract v1.2.0 CreatorContext): the single place in the AI package that turns
it into prompt data, grounding numbers and filters. The brief frames and prioritizes; it never changes numbers.
"""
import re
from typing import Any
from eduhub_ai.features.deterministic import normalize
from eduhub_shared.models import AudienceFilters, CreatorContext, CreatorGoal, PreferredCta

GOAL_LABELS = {
    CreatorGoal.SELL: "vender un producto o servicio",
    CreatorGoal.TRAFFIC: "llevar gente a un link",
    CreatorGoal.REACH: "crecer en alcance",
    CreatorGoal.COMMUNITY: "armar comunidad",
    CreatorGoal.LAUNCH: "lanzar algo nuevo",
    CreatorGoal.OTHER: "otro",
}
CTA_LABELS = {
    PreferredCta.LINK: "link",
    PreferredCta.REPLY: "responder",
    PreferredCta.SAVE: "guardar",
    PreferredCta.SHARE: "compartir",
    PreferredCta.FOLLOW: "seguir",
    PreferredCta.NONE: "ninguno",
}
CONVERSION_GOALS = frozenset({CreatorGoal.SELL, CreatorGoal.TRAFFIC, CreatorGoal.LAUNCH})
PRODUCT_CHARS = 200

def has_brief(context: CreatorContext | None) -> bool:
    """
    True when the creator filled in at least one field.
    """
    return context is not None and context != CreatorContext()

def brief_payload(context: CreatorContext | None) -> dict[str, Any] | None:
    """
    The brief as compact es-AR prompt data, leaving out empty fields; None when nothing is set.
    """
    if not has_brief(context):
        return None
    assert context is not None
    filters = audience_payload(context.audience_filters)
    payload: dict[str, Any] = {
        "objetivo": GOAL_LABELS[context.goal] if context.goal else None,
        "detalle_objetivo": context.goal_detail,
        "oferta": context.offering,
        "audiencia": context.target_audience,
        "audiencia_objetivo": filters or None,
        "voz_de_marca": context.brand_voice,
        "temas_a_evitar": list(context.avoid_topics) or None,
        "cta_preferido": CTA_LABELS[context.preferred_cta] if context.preferred_cta else None,
    }
    return {key: value for key, value in payload.items() if value} or None

def audience_payload(filters: AudienceFilters) -> dict[str, list[str]]:
    """
    Non-empty audience filters with es-AR keys.
    """
    named = {"edades": filters.age_groups, "generos": filters.genders, "provincias": filters.provinces}
    return {key: list(values) for key, values in named.items() if values}

def brief_texts(context: CreatorContext | None) -> list[str]:
    """
    Every free-text field of the brief (grounding allows the numbers in them; see insights.evidence).
    """
    if context is None:
        return []
    fields = [context.goal_detail, context.offering, context.target_audience, context.brand_voice]
    return [text for text in [*fields, *context.avoid_topics] if text]

def mentions_avoided(text: str, context: CreatorContext | None) -> bool:
    """
    True when text mentions one of the brief's avoided topics (whole words, case- and accent-insensitive).
    """
    if context is None or not context.avoid_topics:
        return False
    haystack = normalize(text)
    for topic in context.avoid_topics:
        needle = " ".join(normalize(topic).split())
        if needle and re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack):
            return True
    return False

def wants_conversion(context: CreatorContext | None) -> bool:
    """
    True when the goal needs readers to act outside the post (sell, traffic, launch).
    """
    return context is not None and context.goal in CONVERSION_GOALS

def product_line(context: CreatorContext | None) -> str | None:
    """
    The offering, shortened for the audience role-play prompt.
    """
    if context is None or not context.offering:
        return None
    return context.offering[:PRODUCT_CHARS]
