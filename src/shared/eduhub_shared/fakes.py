"""
Contract C6: deterministic fake implementations of every interface, using only the standard library.

- Back team: build the whole pipeline with them before the AI is ready (and as a demo fallback).
- AI team: use them as a baseline to beat; the real Analyzer must return the same shape.
- Front team: the JSON fixtures are produced by these fakes.
"""
import hashlib
import re
import statistics
import uuid
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo
from eduhub_shared.errors import AccountNotFoundError, AnalysisError
from eduhub_shared.interfaces import ProgressCallback
from eduhub_shared.metrics import aggregate_rates, compute_rates, length_bucket
from eduhub_shared.models import (
    AccountKPIs,
    AccountProfile,
    AccountSnapshot,
    AnalysisReport,
    AnalyzedPost,
    AudienceDimension,
    Draft,
    DraftRequest,
    Evidence,
    Impact,
    Insight,
    InsightCategory,
    Persona,
    PersonaReaction,
    Post,
    PostFeatures,
    PostRates,
    PublishRequest,
    PublishResult,
    PublishStatus,
    ReactionType,
    Recommendation,
    SegmentDimension,
    SegmentReaction,
    SegmentStat,
    SimulationRequest,
    SimulationResult,
    TimeSlotStat,
    Trend,
    VariantResult,
    normalize_handle,
)

AR_TZ = ZoneInfo("America/Argentina/Buenos_Aires")
WEEKDAYS_ES = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
EMOJI_PATTERN = re.compile("[\U0001f300-\U0001faff☀-➿]")
ID_NAMESPACE = uuid.UUID("6f1c2b0e-8d2a-4c41-9a51-2f6a7e0d5b10")
TEXT_ONLY = "text"
VALUE_LABELS_ES = {
    "text": "solo texto",
    "photo": "foto",
    "video": "video",
    "gif": "GIF",
    "short": "corto",
    "medium": "medio",
    "long": "largo",
}
ACTIVE_REACTIONS = (ReactionType.LIKE, ReactionType.REPLY, ReactionType.REPOST, ReactionType.BOOKMARK)
SIMULATION_DISCLAIMER = (
    "Simulación orientativa con audiencias sintéticas basadas en la ENCC 2022-23 (OpenARG). "
    "Sirve para comparar variantes; no predice resultados reales."
)

Clock = Callable[[], datetime]

def utc_now() -> datetime:
    """
    Return the current time in UTC.
    """
    return datetime.now(UTC)

def stable_id(*parts: str) -> str:
    """
    Return a deterministic UUID built from parts.
    """
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))

def format_pct(rate: float) -> str:
    """
    Format a 0..1 rate as an es-AR percentage, e.g. 0.021 -> '2,1%'.
    """
    return f"{rate * 100:.1f}%".replace(".", ",")

def format_multiplier(value: float) -> str:
    """
    Format a score multiplier in es-AR, e.g. 1.5 -> '1,5x'.
    """
    return f"{value:.1f}x".replace(".", ",")

def label_es(value: str) -> str:
    """
    Return the es-AR label of an enum value used in texts (e.g. 'photo' -> 'foto'); other values pass through.
    """
    return VALUE_LABELS_ES.get(value, value)

def format_slot(weekday: int, hour: int) -> str:
    """
    Format a weekday/hour slot in es-AR, e.g. 'martes a las 21 h'.
    """
    return f"{WEEKDAYS_ES[weekday]} a las {hour} h"

def mean_or_none(values: Iterable[float | None]) -> float | None:
    """
    Return the mean of the non-None values, or None if there are none.
    """
    present = [v for v in values if v is not None]
    return statistics.fmean(present) if present else None

def extract_features(post: Post, trends: list[Trend]) -> PostFeatures:
    """
    Extract simple, deterministic features from a post (fake topic = first hashtag).
    """
    local = post.created_at.astimezone(AR_TZ)
    text = post.text
    is_question = "?" in text
    lowered = text.lower()
    trend_names = [t.name.lower().lstrip("#") for t in trends]
    return PostFeatures(
        char_count=len(text),
        word_count=len(text.split()),
        length_bucket=length_bucket(len(text)),
        hour_local=local.hour,
        weekday=local.weekday(),
        media_type=post.media[0] if post.media else None,
        has_link=post.has_link,
        hashtag_count=len(post.hashtags),
        mention_count=len(post.mentions),
        is_question=is_question,
        has_emoji=bool(EMOJI_PATTERN.search(text)),
        topic=post.hashtags[0].lower() if post.hashtags else None,
        tone="conversacional" if is_question else ("entusiasta" if "!" in text else "informativo"),
        sentiment=None,
        matches_trend=any(name and name in lowered for name in trend_names) if trends else None,
    )

def relative_scores(rates: list[PostRates]) -> list[float | None]:
    """
    Score each post as its engagement rate divided by the account's median engagement rate.
    """
    values = [r.engagement_rate for r in rates if r.engagement_rate is not None]
    if not values:
        return [None] * len(rates)
    median = statistics.median(values)
    return [None if r.engagement_rate is None else (r.engagement_rate / median if median else 0.0) for r in rates]

def segment_value(item: AnalyzedPost, dimension: SegmentDimension) -> str | None:
    """
    Return the value of an analyzed post for a segment dimension.
    """
    features = item.features
    values = {
        SegmentDimension.TOPIC: features.topic,
        SegmentDimension.MEDIA_TYPE: features.media_type.value if features.media_type else TEXT_ONLY,
        SegmentDimension.LENGTH_BUCKET: features.length_bucket.value,
        SegmentDimension.TONE: features.tone,
        SegmentDimension.POST_KIND: item.post.kind.value,
        SegmentDimension.HOOK: features.hook,
        SegmentDimension.CTA: features.cta,
    }
    return values[dimension]

def build_heatmap(posts: list[AnalyzedPost]) -> list[TimeSlotStat]:
    """
    Group posts by weekday/hour and average their scores.
    """
    groups: dict[tuple[int, int], list[AnalyzedPost]] = defaultdict(list)
    for item in posts:
        groups[(item.features.weekday, item.features.hour_local)].append(item)
    return [
        TimeSlotStat(weekday=w, hour=h, post_count=len(g), avg_score=mean_or_none(p.score for p in g))
        for (w, h), g in sorted(groups.items())
    ]

def build_segments(posts: list[AnalyzedPost]) -> list[SegmentStat]:
    """
    Compute segment stats for every dimension, best average score first within each dimension.
    """
    segments: list[SegmentStat] = []
    for dimension in SegmentDimension:
        groups: dict[str, list[AnalyzedPost]] = defaultdict(list)
        for item in posts:
            value = segment_value(item, dimension)
            if value is not None:
                groups[value].append(item)
        stats = [
            SegmentStat(
                dimension=dimension,
                value=value,
                post_count=len(group),
                avg_score=mean_or_none(p.score for p in group),
                engagement_rate=aggregate_rates(p.post.metrics for p in group).engagement_rate,
            )
            for value, group in groups.items()
        ]
        segments.extend(sorted(stats, key=lambda s: (s.avg_score is None, -(s.avg_score or 0), s.value)))
    return segments

def best_time_slots(heatmap: list[TimeSlotStat], limit: int = 3) -> list[TimeSlotStat]:
    """
    Return the best slots by average score, preferring slots with at least two posts.
    """
    scored = [s for s in heatmap if s.avg_score is not None]
    reliable = [s for s in scored if s.post_count >= 2] or scored
    return sorted(reliable, key=lambda s: (-(s.avg_score or 0), s.weekday, s.hour))[:limit]

def build_kpis(posts: list[Post]) -> AccountKPIs:
    """
    Compute account KPIs over posts.
    """
    if not posts:
        return AccountKPIs(
            post_count=0, period_start=None, period_end=None, posts_per_week=0.0,
            avg_impressions=None, median_impressions=None, rates=aggregate_rates([]),
        )
    start = min(p.created_at for p in posts)
    end = max(p.created_at for p in posts)
    weeks = max((end - start).total_seconds() / timedelta(weeks=1).total_seconds(), 1.0)
    impressions = [p.metrics.impressions for p in posts if p.metrics.impressions is not None]
    return AccountKPIs(
        post_count=len(posts),
        period_start=start,
        period_end=end,
        posts_per_week=len(posts) / weeks,
        avg_impressions=statistics.fmean(impressions) if impressions else None,
        median_impressions=float(statistics.median(impressions)) if impressions else None,
        rates=aggregate_rates(p.metrics for p in posts),
    )

def impact_for(ratio: float) -> Impact:
    """
    Map a performance ratio to an impact level.
    """
    if ratio >= 1.5:
        return Impact.HIGH
    if ratio >= 1.15:
        return Impact.MEDIUM
    return Impact.LOW

def confidence_for(post_count: int) -> float:
    """
    Return a naive confidence that grows with the number of supporting posts.
    """
    return round(min(1.0, post_count / 10) * 0.8, 2)

def best_segment(segments: list[SegmentStat], dimension: SegmentDimension, min_posts: int = 3) -> SegmentStat | None:
    """
    Return the best-scoring segment of a dimension with at least min_posts posts.
    """
    candidates = [s for s in segments if s.dimension == dimension and s.post_count >= min_posts and s.avg_score]
    return candidates[0] if candidates else None

def worst_segment(segments: list[SegmentStat], dimension: SegmentDimension, min_posts: int = 3) -> SegmentStat | None:
    """
    Return the worst-scoring segment of a dimension with at least min_posts posts.
    """
    candidates = [s for s in segments if s.dimension == dimension and s.post_count >= min_posts and s.avg_score]
    return candidates[-1] if len(candidates) > 1 else None

def build_insights(
    posts: list[AnalyzedPost], segments: list[SegmentStat], slots: list[TimeSlotStat]
) -> list[Insight]:
    """
    Turn the computed stats into template-based es-AR insights.
    """
    insights: list[Insight] = []
    if slots and slots[0].avg_score:
        slot = slots[0]
        ids = [p.post.id for p in posts if (p.features.weekday, p.features.hour_local) == (slot.weekday, slot.hour)]
        insights.append(Insight(
            id="ins-timing",
            category=InsightCategory.TIMING,
            title=f"Tu mejor momento: {format_slot(slot.weekday, slot.hour)}",
            description=(
                f"Los posts publicados los {format_slot(slot.weekday, slot.hour)} rinden "
                f"{format_multiplier(slot.avg_score)} tu post típico."
            ),
            evidence=[
                Evidence(label="Rendimiento vs. tu promedio", value=format_multiplier(slot.avg_score)),
                Evidence(label="Posts en ese horario", value=str(slot.post_count)),
            ],
            impact=impact_for(slot.avg_score),
            confidence=confidence_for(slot.post_count),
            related_post_ids=ids,
        ))
    for dimension, category, label in (
        (SegmentDimension.TOPIC, InsightCategory.TOPIC, "tema"),
        (SegmentDimension.MEDIA_TYPE, InsightCategory.FORMAT, "formato"),
        (SegmentDimension.LENGTH_BUCKET, InsightCategory.LENGTH, "largo"),
    ):
        best = best_segment(segments, dimension)
        worst = worst_segment(segments, dimension)
        if best is None or worst is None or best.value == worst.value:
            continue
        ids = [p.post.id for p in posts if segment_value(p, dimension) == best.value][:10]
        insights.append(Insight(
            id=f"ins-{dimension.value}",
            category=category,
            title=f"El {label} '{label_es(best.value)}' es el que mejor te funciona",
            description=(
                f"Tus posts de {label} '{label_es(best.value)}' rinden {format_multiplier(best.avg_score or 0)} "
                f"tu promedio, contra {format_multiplier(worst.avg_score or 0)} de '{label_es(worst.value)}'."
            ),
            evidence=[
                Evidence(label=f"Engagement '{label_es(best.value)}'", value=format_pct(best.engagement_rate or 0)),
                Evidence(label=f"Engagement '{label_es(worst.value)}'", value=format_pct(worst.engagement_rate or 0)),
                Evidence(label="Posts analizados", value=str(best.post_count)),
            ],
            impact=impact_for((best.avg_score or 0) / max(worst.avg_score or 0, 0.01)),
            confidence=confidence_for(best.post_count),
            related_post_ids=ids,
        ))
    return insights

def build_recommendations(insights: list[Insight]) -> list[Recommendation]:
    """
    Turn each insight into one concrete es-AR recommendation.
    """
    actions = {
        InsightCategory.TIMING: "Programá tus próximos posts en ese horario",
        InsightCategory.TOPIC: "Publicá más sobre tu tema más fuerte esta semana",
        InsightCategory.FORMAT: "Repetí el formato que mejor te funciona",
        InsightCategory.LENGTH: "Ajustá el largo de tus posts al que mejor rinde",
    }
    return [
        Recommendation(
            id=f"rec-{index}",
            category=insight.category,
            action=actions.get(insight.category, "Probá repetir este patrón"),
            rationale=insight.description,
            priority=index,
            based_on_insight_ids=[insight.id],
        )
        for index, insight in enumerate(insights, start=1)
    ]

def explain(item: AnalyzedPost, best_slots: list[TimeSlotStat], top: bool) -> str:
    """
    Write a short es-AR explanation of why a post performed well or badly.
    """
    score = format_multiplier(item.score or 0)
    reasons = []
    if (item.features.weekday, item.features.hour_local) in {(s.weekday, s.hour) for s in best_slots}:
        reasons.append("salió en uno de tus mejores horarios")
    if item.features.topic:
        reasons.append(f"tema '{item.features.topic}'")
    media = item.features.media_type.value if item.features.media_type else TEXT_ONLY
    reasons.append(f"formato '{label_es(media)}'")
    prefix = f"Rindió {score} tu promedio" if top else f"Rindió por debajo de tu promedio ({score})"
    return f"{prefix}: {', '.join(reasons)}."

def with_explanations(posts: list[AnalyzedPost], best_slots: list[TimeSlotStat], count: int = 3) -> list[AnalyzedPost]:
    """
    Add explanations to the top and bottom posts by score.
    """
    ranked = sorted((p for p in posts if p.score is not None), key=lambda p: (-(p.score or 0), p.post.id))
    top_ids = {p.post.id for p in ranked[:count]}
    bottom_ids = {p.post.id for p in ranked[-count:]} - top_ids
    result = []
    for item in posts:
        if item.post.id in top_ids or item.post.id in bottom_ids:
            item = item.model_copy(update={"explanation": explain(item, best_slots, item.post.id in top_ids)})
        result.append(item)
    return result

def build_summary(profile: AccountProfile, kpis: AccountKPIs, insights: list[Insight]) -> str:
    """
    Write a 2-4 sentence es-AR summary of the analysis.
    """
    rate = kpis.rates.engagement_rate
    parts = [f"Analizamos {kpis.post_count} posts de @{profile.handle}."]
    if rate is not None:
        parts.append(f"Tu engagement promedio es {format_pct(rate)}.")
    parts.extend(insight.title + "." for insight in insights[:2])
    return " ".join(parts)

class FakeAnalyzer:
    """
    Deterministic baseline Analyzer: real stats, template-based texts, no LLM.
    """
    def __init__(self, clock: Clock = utc_now) -> None:
        """
        Use clock to timestamp reports (inject a fixed clock for reproducible output).
        """
        self._clock = clock

    async def analyze(self, snapshot: AccountSnapshot, on_progress: ProgressCallback | None = None) -> AnalysisReport:
        """
        Analyze every post of snapshot and return a report.
        """
        if not snapshot.posts:
            raise AnalysisError("La cuenta no tiene posts para analizar.")
        if on_progress:
            await on_progress(0.2, "Extrayendo características de los posts")
        rates = [compute_rates(p.metrics) for p in snapshot.posts]
        scores = relative_scores(rates)
        posts = [
            AnalyzedPost(post=p, features=extract_features(p, snapshot.trends), rates=r, score=s)
            for p, r, s in zip(snapshot.posts, rates, scores, strict=True)
        ]
        if on_progress:
            await on_progress(0.6, "Calculando métricas y patrones")
        heatmap = build_heatmap(posts)
        segments = build_segments(posts)
        slots = best_time_slots(heatmap)
        kpis = build_kpis(snapshot.posts)
        if on_progress:
            await on_progress(0.9, "Generando insights y recomendaciones")
        insights = build_insights(posts, segments, slots)
        generated_at = self._clock()
        return AnalysisReport(
            id=stable_id("report", snapshot.profile.handle, generated_at.isoformat()),
            profile=snapshot.profile,
            generated_at=generated_at,
            kpis=kpis,
            posts=with_explanations(posts, slots),
            heatmap=heatmap,
            segments=segments,
            best_time_slots=slots,
            insights=insights,
            recommendations=build_recommendations(insights),
            summary=build_summary(snapshot.profile, kpis, insights),
            engine="fake",
            context=snapshot.context,
        )

DRAFT_TEMPLATES = (
    "Hilo rápido sobre {topic}: 3 cosas que me hubiera gustado saber antes 👇",
    "¿Qué es lo que más te cuesta de {topic}? Leo todas las respuestas y armo un post con las mejores.",
    "Error que veo todo el tiempo con {topic}: dejarlo para fin de mes. Hacelo el día que cobrás.",
    "Guardate este post: mi checklist de {topic} en 5 pasos, simple y sin vueltas.",
    "Opinión impopular sobre {topic}: no necesitás una app, necesitás un hábito.",
)

def next_slot_after(moment: datetime, weekday: int, hour: int) -> datetime:
    """
    Return the next datetime (UTC) after moment that falls on weekday/hour in Argentina time.
    """
    local = moment.astimezone(AR_TZ).replace(minute=0, second=0, microsecond=0)
    days_ahead = (weekday - local.weekday()) % 7
    candidate = (local + timedelta(days=days_ahead)).replace(hour=hour)
    if candidate <= moment:
        candidate += timedelta(days=7)
    return candidate.astimezone(UTC)

class FakeDraftGenerator:
    """
    Deterministic DraftGenerator based on templates and the report's best topic and time slot.
    """
    def __init__(self, clock: Clock = utc_now) -> None:
        """
        Use clock to compute suggested times (inject a fixed clock for reproducible output).
        """
        self._clock = clock

    async def generate(self, request: DraftRequest, report: AnalysisReport, trends: list[Trend]) -> list[Draft]:
        """
        Return request.count template drafts about the requested or best topic.
        """
        best_topic = best_segment(report.segments, SegmentDimension.TOPIC, min_posts=1)
        topic = request.topic or (best_topic.value if best_topic else "tu tema principal")
        now = self._clock()
        slot = report.best_time_slots[0] if report.best_time_slots else None
        suggested = next_slot_after(now, slot.weekday, slot.hour) if slot else None
        insight_ids = [i.id for i in report.insights[:2]]
        return [
            Draft(
                id=stable_id("draft", report.profile.handle, topic, str(index), now.isoformat()),
                text=DRAFT_TEMPLATES[index % len(DRAFT_TEMPLATES)].format(topic=topic),
                rationale=f"Basado en tu tema más fuerte ('{topic}') y en tu mejor horario.",
                suggested_time=suggested,
                estimated_score=best_topic.avg_score if best_topic else None,
                based_on_insight_ids=insight_ids,
            )
            for index in range(request.count)
        ]

FAKE_PERSONAS = (
    Persona(id="p-01", age_group="18 a 29 años", gender="Mujer", province="Ciudad Autónoma de Buenos Aires",
            socioeconomic_level="Medio", platforms=["x", "instagram"], traits=["estudiante", "ahorra en dólares"],
            weight=9200.0),
    Persona(id="p-02", age_group="18 a 29 años", gender="Varón", province="Buenos Aires", socioeconomic_level="Bajo",
            platforms=["x", "tiktok"], traits=["primer trabajo", "fan del fútbol"], weight=12100.0),
    Persona(id="p-03", age_group="30 a 49 años", gender="Mujer", province="Córdoba", socioeconomic_level="Medio",
            platforms=["x", "facebook"], traits=["madre", "emprendedora"], weight=10400.0),
    Persona(id="p-04", age_group="30 a 49 años", gender="Varón", province="Santa Fe", socioeconomic_level="Alto",
            platforms=["x", "linkedin"], traits=["profesional", "invierte"], weight=7800.0),
    Persona(id="p-05", age_group="13 a 17 años", gender="Mujer", province="Mendoza", socioeconomic_level="Medio",
            platforms=["x", "tiktok", "instagram"], traits=["secundaria", "sigue influencers"], weight=6100.0),
    Persona(id="p-06", age_group="50 a 64 años", gender="Varón", province="Tucumán", socioeconomic_level="Bajo",
            platforms=["x", "facebook"], traits=["comerciante", "lee noticias"], weight=5300.0),
    Persona(id="p-07", age_group="18 a 29 años", gender="Mujer", province="Buenos Aires", socioeconomic_level="Alto",
            platforms=["x", "instagram"], traits=["freelancer", "cobra en dólares"], weight=8700.0),
    Persona(id="p-08", age_group="30 a 49 años", gender="Varón", province="Ciudad Autónoma de Buenos Aires",
            socioeconomic_level="Medio", platforms=["x"], traits=["programador", "crítico"], weight=9900.0),
    Persona(id="p-09", age_group="65 años y mas", gender="Mujer", province="Buenos Aires", socioeconomic_level="Medio",
            platforms=["x", "whatsapp"], traits=["jubilada", "cuida el presupuesto"], weight=3200.0),
    Persona(id="p-10", age_group="18 a 29 años", gender="Varón", province="Córdoba", socioeconomic_level="Medio",
            platforms=["x", "twitch"], traits=["universitario", "gamer"], weight=8800.0),
    Persona(id="p-11", age_group="30 a 49 años", gender="Mujer", province="Buenos Aires", socioeconomic_level="Bajo",
            platforms=["x", "tiktok"], traits=["empleada", "busca ingresos extra"], weight=11300.0),
    Persona(id="p-12", age_group="50 a 64 años", gender="Mujer", province="Santa Fe", socioeconomic_level="Alto",
            platforms=["x", "facebook"], traits=["docente", "comparte consejos"], weight=4600.0),
)

def deterministic_reaction(persona_id: str, text: str) -> ReactionType:
    """
    Pick a reaction from a hash of persona and text; questions get more replies, short texts more likes.
    """
    bucket = int(hashlib.sha256(f"{persona_id}|{text}".encode()).hexdigest(), 16) % 100
    if "?" in text and bucket < 15:
        return ReactionType.REPLY
    if len(text) <= 140 and bucket < 30:
        return ReactionType.LIKE
    thresholds = (
        (20, ReactionType.IGNORE), (45, ReactionType.READ), (70, ReactionType.LIKE),
        (80, ReactionType.REPLY), (88, ReactionType.REPOST),
    )
    return next((reaction for limit, reaction in thresholds if bucket < limit), ReactionType.BOOKMARK)

def weighted_interaction_rate(personas: list[Persona], reactions: list[PersonaReaction]) -> float:
    """
    Return the weighted share of personas with an active reaction.
    """
    weights = {p.id: p.weight for p in personas}
    total = sum(weights[r.persona_id] for r in reactions)
    active = sum(weights[r.persona_id] for r in reactions if r.reaction in ACTIVE_REACTIONS)
    return active / total if total else 0.0

def select_personas(request: SimulationRequest) -> list[Persona]:
    """
    Filter the fake personas and repeat them (with suffixed ids) up to request.audience_size.
    """
    filters = request.filters
    pool = [
        p for p in FAKE_PERSONAS
        if (not filters.age_groups or p.age_group in filters.age_groups)
        and (not filters.genders or p.gender in filters.genders)
        and (not filters.provinces or p.province in filters.provinces)
    ] or list(FAKE_PERSONAS)
    return [
        pool[i % len(pool)].model_copy(update={"id": f"{pool[i % len(pool)].id}-{i // len(pool)}"})
        for i in range(request.audience_size)
    ]

class FakeAudienceSimulator:
    """
    Deterministic AudienceSimulator using hard-coded personas shaped like ENCC respondents.
    """
    def __init__(self, clock: Clock = utc_now) -> None:
        """
        Use clock to build the result id (inject a fixed clock for reproducible output).
        """
        self._clock = clock

    async def simulate(self, request: SimulationRequest) -> SimulationResult:
        """
        Simulate one reaction per persona and variant, and aggregate by variant and segment.
        """
        personas = select_personas(request)
        reactions = [
            PersonaReaction(persona_id=p.id, variant_index=i, reaction=deterministic_reaction(p.id[:4], text))
            for i, text in enumerate(request.variants)
            for p in personas
        ]
        variants = []
        segments = []
        for index, text in enumerate(request.variants):
            variant_reactions = [r for r in reactions if r.variant_index == index]
            counts = {t: sum(1 for r in variant_reactions if r.reaction == t) for t in ReactionType}
            variants.append(VariantResult(
                variant_index=index, text=text, reaction_counts=counts,
                interaction_rate=weighted_interaction_rate(personas, variant_reactions),
            ))
            for dimension in (AudienceDimension.AGE_GROUP, AudienceDimension.GENDER):
                values = sorted({getattr(p, dimension.value) for p in personas})
                for value in values:
                    members = [p for p in personas if getattr(p, dimension.value) == value]
                    ids = {p.id for p in members}
                    segments.append(SegmentReaction(
                        dimension=dimension, value=value, variant_index=index, persona_count=len(members),
                        interaction_rate=weighted_interaction_rate(
                            members, [r for r in variant_reactions if r.persona_id in ids]
                        ),
                    ))
        best = max(variants, key=lambda v: (v.interaction_rate, -v.variant_index))
        return SimulationResult(
            id=stable_id("simulation", *request.variants, self._clock().isoformat()),
            personas=personas,
            reactions=reactions,
            variants=variants,
            segments=segments,
            best_variant_index=best.variant_index,
            summary=(
                f"La variante {best.variant_index + 1} generó más interacción "
                f"({format_pct(best.interaction_rate)} de la audiencia simulada)."
            ),
            disclaimer=SIMULATION_DISCLAIMER,
        )

class FakePostSource:
    """
    PostSource that replays a saved AccountSnapshot (defaults to the shared fixture).
    """
    def __init__(self, snapshot: AccountSnapshot | None = None) -> None:
        """
        Replay snapshot, or the shared fixture snapshot when None.
        """
        if snapshot is None:
            from eduhub_shared.fixtures import load_snapshot
            snapshot = load_snapshot()
        self._snapshot = snapshot

    def _check(self, handle: str) -> None:
        """
        Raise AccountNotFoundError unless handle is the snapshot's account.
        """
        if normalize_handle(handle) != self._snapshot.profile.handle:
            raise AccountNotFoundError(f"No encontramos la cuenta @{handle.lstrip('@')}.")

    async def fetch_profile(self, handle: str) -> AccountProfile:
        """
        Return the snapshot profile.
        """
        self._check(handle)
        return self._snapshot.profile

    async def fetch_posts(self, handle: str, limit: int) -> list[Post]:
        """
        Return up to limit snapshot posts, newest first.
        """
        self._check(handle)
        return self._snapshot.posts[:limit]

    async def fetch_trends(self, location: str = "Argentina") -> list[Trend]:
        """
        Return the snapshot trends.
        """
        return list(self._snapshot.trends)

class FakePostPublisher:
    """
    PostPublisher that never calls X: schedules are echoed and immediate posts return an X compose (intent) URL.
    """
    async def publish(self, request: PublishRequest) -> PublishResult:
        """
        Return SCHEDULED for scheduled requests, otherwise INTENT with a pre-filled compose URL.
        """
        if request.scheduled_for is not None:
            return PublishResult(status=PublishStatus.SCHEDULED, scheduled_for=request.scheduled_for)
        return PublishResult(status=PublishStatus.INTENT, url=f"https://x.com/intent/post?text={quote(request.text)}")
