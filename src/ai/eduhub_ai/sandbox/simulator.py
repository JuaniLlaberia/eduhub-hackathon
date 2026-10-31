"""
LLMAudienceSimulator: role-plays a sample of ENCC personas reacting to 1-3 post variants (one cheap LLM call per
batch of personas, all variants at once) and aggregates the reactions with the survey weights, by variant and
by audience segment. It compares variants; it does not predict real engagement (the disclaimer says so).
"""
import asyncio
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pydantic import BaseModel, ConfigDict, Field
from eduhub_ai.config import AISettings
from eduhub_ai.context import product_line
from eduhub_ai.llm.client import LLMClient, LLMError
from eduhub_ai.sandbox.personas import load_personas, sample_personas
from eduhub_ai.sandbox.prompts import SANDBOX_SYSTEM, sandbox_user
from eduhub_shared.errors import SimulationError
from eduhub_shared.models import (
    AudienceDimension,
    AudienceFilters,
    Persona,
    PersonaReaction,
    ReactionType,
    SegmentReaction,
    SimulationRequest,
    SimulationResult,
    VariantResult,
)

BATCH_SIZE = 10
SANDBOX_TEMPERATURE = 0.7
MIN_SEGMENT_PERSONAS = 3
SIMULATION_NAMESPACE = uuid.UUID("9c1e5a72-3f84-4d6b-b0a9-2e7d18c4f655")
ACTIVE = frozenset({ReactionType.LIKE, ReactionType.REPLY, ReactionType.REPOST, ReactionType.BOOKMARK})
DISCLAIMER = (
    "Simulación orientativa con audiencias sintéticas basadas en la ENCC 2022-23 (OpenARG). "
    "Sirve para comparar variantes; no predice resultados reales."
)
BRIEF_AUDIENCE_NOTE = " (Simulado con la audiencia objetivo de tu brief.)"
NO_AUDIENCE = "No encontramos personas para esa audiencia. Probá con menos filtros."
FAILED = "No pudimos simular la audiencia. Probá de nuevo en unos minutos."
logger = logging.getLogger(__name__)

class ReactionDraft(BaseModel):
    """
    One persona's reaction to one variant, as role-played by the LLM.
    """
    model_config = ConfigDict(extra="forbid")
    persona_id: str
    variant_index: int
    reaction: ReactionType
    comment: str | None
    sentiment: float = Field(ge=-1, le=1)

class ReactionsResponse(BaseModel):
    """
    All reactions of one batch.
    """
    model_config = ConfigDict(extra="forbid")
    reactions: list[ReactionDraft]

def utc_now() -> datetime:
    """
    The current time in UTC.
    """
    return datetime.now(UTC)

class LLMAudienceSimulator:
    """
    AudienceSimulator backed by the label (cheap) model. personas=None loads the packaged ENCC personas.
    """
    def __init__(
        self,
        settings: AISettings,
        client: LLMClient,
        clock: Callable[[], datetime] = utc_now,
        personas: list[Persona] | None = None,
        seed: int = 0,
    ) -> None:
        """
        Keep the settings, the LLM client, the clock (for the result id), the persona pool and the sample seed.
        """
        self.settings = settings
        self.client = client
        self._clock = clock
        self._personas = personas
        self.seed = seed

    async def simulate(self, request: SimulationRequest) -> SimulationResult:
        """
        Sample the audience, role-play every persona × variant and aggregate. Raises SimulationError (es-AR)
        when no persona matches the filters or more than half the reactions are missing.
        """
        pool = self._personas if self._personas is not None else load_personas()
        filters, from_brief = audience_filters(request)
        personas = sample_personas(pool, filters, request.audience_size, self.seed)
        if not personas:
            raise SimulationError(NO_AUDIENCE)
        batches = [personas[i:i + BATCH_SIZE] for i in range(0, len(personas), BATCH_SIZE)]
        product = product_line(request.context)
        answers = await asyncio.gather(*[self._react(batch, request.variants, product) for batch in batches])
        reactions = [reaction for batch in answers for reaction in batch]
        expected = len(personas) * len(request.variants)
        if len(reactions) * 2 < expected:
            logger.warning("simulation got %d of %d reactions", len(reactions), expected)
            raise SimulationError(FAILED)
        return self._result(request, personas, reactions, from_brief)

    async def _react(self, batch: list[Persona], variants: list[str], product: str | None) -> list[PersonaReaction]:
        """
        One LLM call for a batch; keeps one valid reaction per (persona, variant). A failed call yields none.
        """
        payload = {
            "personas": [persona_card(p) for p in batch],
            "variantes": [{"indice": i, "texto": text} for i, text in enumerate(variants)],
        }
        if product is not None:
            payload["producto"] = product
        try:
            response = await self.client.complete_json(
                model=self.settings.label_model, system=SANDBOX_SYSTEM, user=sandbox_user(payload),
                schema=ReactionsResponse, temperature=SANDBOX_TEMPERATURE, reasoning=self.settings.label_reasoning,
            )
        except LLMError as error:
            logger.warning("simulation batch of %d personas failed: %s", len(batch), error)
            return []
        ids = {p.id for p in batch}
        kept: dict[tuple[str, int], PersonaReaction] = {}
        for draft in response.reactions:
            key = (draft.persona_id, draft.variant_index)
            if draft.persona_id in ids and 0 <= draft.variant_index < len(variants) and key not in kept:
                kept[key] = PersonaReaction(persona_id=draft.persona_id, variant_index=draft.variant_index,
                                            reaction=draft.reaction, comment=draft.comment,
                                            sentiment=draft.sentiment)
        return list(kept.values())

    def _result(
        self, request: SimulationRequest, personas: list[Persona], reactions: list[PersonaReaction],
        from_brief: bool = False,
    ) -> SimulationResult:
        """
        Aggregate by variant and by segment, pick the best variant and write the es-AR summary.
        """
        variants = [variant_result(i, text, personas, reactions) for i, text in enumerate(request.variants)]
        segments = [s for i in range(len(request.variants)) for s in segment_results(i, personas, reactions)]
        best = max(variants, key=lambda v: (v.interaction_rate, -v.variant_index))
        return SimulationResult(
            id=str(uuid.uuid5(SIMULATION_NAMESPACE, "|".join([*request.variants, self._clock().isoformat()]))),
            personas=personas,
            reactions=reactions,
            variants=variants,
            segments=segments,
            best_variant_index=best.variant_index,
            summary=summary(best, variants, segments) + (BRIEF_AUDIENCE_NOTE if from_brief else ""),
            disclaimer=DISCLAIMER,
        )

def audience_filters(request: SimulationRequest) -> tuple[AudienceFilters, bool]:
    """
    The request's filters, or the brief's target audience when the request sets none; plus whether the brief's
    were used.
    """
    brief = request.context.audience_filters if request.context is not None else AudienceFilters()
    if request.filters == AudienceFilters() and brief != AudienceFilters():
        return brief, True
    return request.filters, False

def persona_card(persona: Persona) -> dict[str, object]:
    """
    What the LLM sees about a persona (no weight: it should not bias the role-play).
    """
    return {"id": persona.id, "edad": persona.age_group, "genero": persona.gender, "provincia": persona.province,
            "nivel": persona.socioeconomic_level, "plataformas": persona.platforms, "habitos": persona.traits}

def weighted_rate(personas: list[Persona], reactions: list[PersonaReaction]) -> float:
    """
    Survey-weighted share of reactions that are active (like, reply, repost, bookmark).
    """
    weights = {p.id: p.weight for p in personas}
    counted = [r for r in reactions if r.persona_id in weights]
    total = sum(weights[r.persona_id] for r in counted)
    active = sum(weights[r.persona_id] for r in counted if r.reaction in ACTIVE)
    return active / total if total else 0.0

def variant_result(
    index: int, text: str, personas: list[Persona], reactions: list[PersonaReaction]
) -> VariantResult:
    """
    Counts and weighted interaction rate of one variant.
    """
    own = [r for r in reactions if r.variant_index == index]
    counts = {t: sum(1 for r in own if r.reaction == t) for t in ReactionType}
    return VariantResult(variant_index=index, text=text, interaction_rate=weighted_rate(personas, own),
                         reaction_counts=counts)

def segment_results(index: int, personas: list[Persona], reactions: list[PersonaReaction]) -> list[SegmentReaction]:
    """
    Weighted interaction rate of one variant for every value of every AudienceDimension.
    """
    own = [r for r in reactions if r.variant_index == index]
    results = []
    for dimension in AudienceDimension:
        values = sorted({v for p in personas if (v := getattr(p, dimension.value)) is not None})
        for value in values:
            members = [p for p in personas if getattr(p, dimension.value) == value]
            results.append(SegmentReaction(dimension=dimension, value=value, variant_index=index,
                                           persona_count=len(members), interaction_rate=weighted_rate(members, own)))
    return results

def times(ratio: float) -> str:
    """
    es-AR multiplier in words, e.g. 1.52 -> "1,5 veces".
    """
    return f"{ratio:.1f} veces".replace(".", ",")

def summary(best: VariantResult, variants: list[VariantResult], segments: list[SegmentReaction]) -> str:
    """
    es-AR summary that compares variants instead of quoting rates (LLM role-play ranks variants consistently but
    is not calibrated in absolute terms), plus the age group where the winner did best.
    """
    others = sorted((v for v in variants if v.variant_index != best.variant_index), key=lambda v: -v.interaction_rate)
    if not others:
        text = ("Con una sola variante no hay con qué comparar: sumá una o dos versiones del post para ver cuál "
                "funciona mejor con la audiencia simulada.")
    elif others[0].interaction_rate <= 0:
        text = (f"La variante {best.variant_index + 1} fue la única que generó interacción en la audiencia "
                "simulada.")
    elif best.interaction_rate == others[0].interaction_rate:
        text = "Las variantes generaron una interacción parecida en la audiencia simulada: no hay una ganadora clara."
    else:
        ratio = times(best.interaction_rate / others[0].interaction_rate)
        text = (f"La variante {best.variant_index + 1} generó {ratio} más interacción que la variante "
                f"{others[0].variant_index + 1} en la audiencia simulada.")
    ages = [s for s in segments if s.variant_index == best.variant_index and s.dimension == AudienceDimension.AGE_GROUP
            and s.persona_count >= MIN_SEGMENT_PERSONAS]
    if others and ages:
        top = max(ages, key=lambda s: (s.interaction_rate, s.value))
        text += f" Donde mejor funcionó fue entre personas de {top.value}."
    return text
