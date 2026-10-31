"""
The evidence pack: everything the insight writer may say, computed in code and pre-formatted in es-AR
("2,1%", "1,4x", "21 h"). The LLM only references items by id and copies their numbers; Insight.evidence and
confidence are built from these items in code.
"""
import json
from collections.abc import Callable
from typing import Literal
from pydantic import BaseModel, Field
from eduhub_ai.features.deterministic import hour_block
from eduhub_ai.insights.grounding import extract_numbers
from eduhub_ai.stats.segments import SegmentDetail, segment_details, segment_value
from eduhub_ai.stats.significance import is_significant
from eduhub_ai.stats.timing import day_type, hour_block_stats
from eduhub_shared.models import (
    AccountKPIs,
    AccountProfile,
    AnalyzedPost,
    InsightCategory,
    SegmentDimension,
    TimeSlotStat,
)

MAX_FINDINGS = 12
TOP_POSTS = 5
RELATED_POSTS = 10
POST_TEXT_CHARS = 280
WEEKDAYS_ES = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
CATEGORIES = {
    SegmentDimension.TOPIC.value: InsightCategory.TOPIC,
    SegmentDimension.MEDIA_TYPE.value: InsightCategory.FORMAT,
    SegmentDimension.POST_KIND.value: InsightCategory.FORMAT,
    SegmentDimension.LENGTH_BUCKET.value: InsightCategory.LENGTH,
    SegmentDimension.TONE.value: InsightCategory.TONE,
    SegmentDimension.HOOK.value: InsightCategory.HOOK,
    SegmentDimension.CTA.value: InsightCategory.CTA,
    "hour_block": InsightCategory.TIMING,
    "day_type": InsightCategory.TIMING,
    "hour_block_day_type": InsightCategory.TIMING,
}
DIMENSION_LABELS = {
    "topic": "Tema", "media_type": "Formato", "post_kind": "Tipo de post", "length_bucket": "Largo",
    "tone": "Tono", "hook": "Gancho", "cta": "Llamado a la acción", "hour_block": "Franja",
    "day_type": "Días", "hour_block_day_type": "Franja y días",
}
VALUE_LABELS = {
    "text": "solo texto", "photo": "foto", "video": "video", "gif": "GIF", "short": "corto", "medium": "medio",
    "long": "largo", "original": "original", "quote": "cita", "reply": "respuesta", "repost": "repost",
}
MEDIA_SUBJECTS = {"text": "de solo texto", "photo": "con foto", "video": "con video", "gif": "con GIF"}
LENGTH_SUBJECTS = {"short": "cortos", "medium": "de largo medio", "long": "largos"}
KIND_SUBJECTS = {"original": "posts originales", "quote": "citas"}
HOOK_SUBJECTS = {"pregunta": "una pregunta", "dato": "un dato", "afirmación fuerte": "una afirmación fuerte",
                 "historia": "una historia", "lista": "una lista"}
CTA_SUBJECTS = {"guardar": "que lo guarden", "responder": "respuestas", "compartir": "que lo compartan",
                "seguir": "que te sigan", "link": "ir a un link"}
BLOCK_SUBJECTS = {"madrugada": "de la madrugada", "mañana": "de la mañana", "mediodía": "del mediodía",
                  "tarde": "de la tarde", "noche": "de la noche"}
DAY_SUBJECTS = {"semana": "de lunes a viernes", "fin de semana": "del fin de semana"}

class EvidenceItem(BaseModel):
    """
    One citable data point. label/value are what Insight.evidence shows; numbers are its formatted figures.
    direction is "up" when the segment beats the account's other posts (lift >= 1), "down" otherwise.
    subject/short are es-AR phrases for templates ("tus posts con video" / "posts con video").
    """
    id: str
    kind: Literal["kpi", "segment", "timing", "slot", "pattern"]
    category: InsightCategory
    label: str
    value: str
    numbers: dict[str, str] = Field(default_factory=dict)
    direction: Literal["up", "down", "flat"] = "flat"
    subject: str = ""
    short: str = ""
    lift: float | None = None
    confidence: float | None = None
    related_post_ids: list[str] = Field(default_factory=list)

class PostEvidence(BaseModel):
    """
    A top or bottom post as the writer sees it: text, labels and formatted score.
    """
    id: str
    rank: Literal["top", "bottom"]
    score: str
    text: str
    topic: str | None
    tone: str | None
    hook: str | None
    cta: str | None
    formato: str
    largo: str
    franja: str
    dia: str
    hora: str

class EvidencePack(BaseModel):
    """
    All evidence for one account. allowed_numbers holds every number token that may appear in the texts.
    """
    handle: str
    post_count: int
    kpis: list[EvidenceItem]
    findings: list[EvidenceItem]
    best_slots: list[EvidenceItem]
    top_posts: list[PostEvidence]
    bottom_posts: list[PostEvidence]
    pattern_effects: list[EvidenceItem] = Field(default_factory=list)
    post_ids: set[str] = Field(default_factory=set)
    allowed_numbers: set[str] = Field(default_factory=set)

    def items(self) -> list[EvidenceItem]:
        """
        Every citable item, in prompt order.
        """
        return [*self.kpis, *self.findings, *self.best_slots, *self.pattern_effects]

    def item(self, item_id: str) -> EvidenceItem | None:
        """
        The item with this id, or None.
        """
        return next((i for i in self.items() if i.id == item_id), None)

    def prompt_json(self) -> str:
        """
        Compact JSON for the writer prompt (no internal fields such as confidence or allowed_numbers).
        """
        public = {"id", "label", "value", "numbers", "direction"}
        payload = {
            "cuenta": f"@{self.handle}",
            "kpis": [i.model_dump(include=public) for i in self.kpis],
            "findings": [i.model_dump(include=public) for i in self.findings],
            "mejores_horarios": [i.model_dump(include=public) for i in self.best_slots],
            "efectos_modelo": [i.model_dump(include=public) for i in self.pattern_effects],
            "top_posts": [p.model_dump() for p in self.top_posts],
            "bottom_posts": [p.model_dump() for p in self.bottom_posts],
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

def fmt_x(value: float) -> str:
    """
    Multiplier vs the typical post, e.g. 1.43 -> "1,4x".
    """
    return f"{value:.1f}x".replace(".", ",")

def fmt_pct(rate: float) -> str:
    """
    Percentage of a 0..1 rate, e.g. 0.021 -> "2,1%".
    """
    return f"{rate * 100:.1f}%".replace(".", ",")

def fmt_int(value: float) -> str:
    """
    Integer with es-AR thousands dots, e.g. 3386 -> "3.386".
    """
    return f"{round(value):,}".replace(",", ".")

def fmt_dec(value: float) -> str:
    """
    One-decimal number, e.g. 4.14 -> "4,1".
    """
    return f"{value:.1f}".replace(".", ",")

def confidence_for(detail: SegmentDetail) -> float:
    """
    Confidence in 0..1 from the stats only: more posts and a narrower CI (relative to the median) mean more.
    """
    size = min(detail.n, 30) / 30
    width = (detail.ci_high - detail.ci_low) / max(detail.median_score, 0.01)
    return round(min(1.0, 0.2 + 0.5 * size + 0.3 / (1 + width)), 2)

def build_evidence(
    profile: AccountProfile,
    kpis: AccountKPIs,
    posts: list[AnalyzedPost],
    best_slots: list[TimeSlotStat],
    max_findings: int = MAX_FINDINGS,
    top_n: int = TOP_POSTS,
    pattern_effects: list[EvidenceItem] | None = None,
) -> EvidencePack:
    """
    Build the evidence pack: KPIs, significant segment and timing findings, best slots, top/bottom posts and
    the pattern model's effects (stage 07) when given.
    """
    scored = sorted((p for p in posts if p.score is not None), key=lambda p: (-(p.score or 0), p.post.id))
    top = scored[:top_n]
    bottom = [p for p in scored[::-1][:top_n] if p not in top]
    pack = EvidencePack(
        handle=profile.handle,
        post_count=kpis.post_count,
        kpis=kpi_items(kpis, len(scored)),
        findings=finding_items(posts, max_findings),
        best_slots=[slot_item(slot, scored) for slot in best_slots],
        top_posts=[post_evidence(p, "top") for p in top],
        bottom_posts=[post_evidence(p, "bottom") for p in bottom],
        pattern_effects=list(pattern_effects or []),
        post_ids={p.post.id for p in posts},
    )
    return pack.model_copy(update={"allowed_numbers": extract_numbers(pack.prompt_json())})

def kpi_items(kpis: AccountKPIs, scored_count: int) -> list[EvidenceItem]:
    """
    KPI evidence items (rates that are missing are skipped).
    """
    rows: list[tuple[str, str, str | None]] = [
        ("posts", "Posts analizados", str(kpis.post_count)),
        ("scorable", "Posts con puntaje", str(scored_count)),
        ("posts_per_week", "Posts por semana", fmt_dec(kpis.posts_per_week)),
        ("median_impressions", "Vistas medianas",
         fmt_int(kpis.median_impressions) if kpis.median_impressions is not None else None),
    ]
    rates = kpis.rates
    for key, label, rate in (
        ("engagement_rate", "Engagement promedio", rates.engagement_rate),
        ("save_rate", "Tasa de guardados", rates.save_rate),
        ("share_rate", "Tasa de compartidos", rates.share_rate),
        ("reply_rate", "Tasa de respuestas", rates.reply_rate),
    ):
        rows.append((key, label, fmt_pct(rate) if rate is not None else None))
    return [
        EvidenceItem(id=f"kpi:account:{key}", kind="kpi", category=InsightCategory.OTHER, label=label, value=value,
                     numbers={"valor": value})
        for key, label, value in rows if value is not None
    ]

def finding_items(posts: list[AnalyzedPost], max_findings: int) -> list[EvidenceItem]:
    """
    Significant segment and timing details that compare against other posts, strongest evidence first.
    """
    details = [*segment_details(posts), *hour_block_stats(posts)]
    kept = [d for d in details if d.lift_vs_rest is not None and is_significant(d)]
    kept.sort(key=lambda d: (d.p_value if d.p_value is not None else 1.0, -d.n, d.dimension, d.value))
    return [finding_item(d, posts) for d in kept[:max_findings]]

def finding_item(detail: SegmentDetail, posts: list[AnalyzedPost]) -> EvidenceItem:
    """
    Turn one SegmentDetail into an evidence item with formatted numbers and es-AR phrases.
    """
    timing = CATEGORIES[detail.dimension] == InsightCategory.TIMING
    numbers = {
        "mediana": fmt_x(detail.median_score),
        "posts": str(detail.n),
        "vs_resto": fmt_x(detail.lift_vs_rest or 0),
        "rango": f"{fmt_x(detail.ci_low)} a {fmt_x(detail.ci_high)}",
    }
    subject = subject_for(detail.dimension, detail.value)
    members = [p for p in posts if p.score is not None and member_value(p, detail.dimension) == detail.value]
    members.sort(key=lambda p: (-(p.score or 0), p.post.id))
    return EvidenceItem(
        id=f"{'time' if timing else 'seg'}:{detail.dimension}:{detail.value}",
        kind="timing" if timing else "segment",
        category=CATEGORIES[detail.dimension],
        label=f"{DIMENSION_LABELS[detail.dimension]} '{VALUE_LABELS.get(detail.value, detail.value)}'",
        value=f"{numbers['mediana']} tu post típico en {numbers['posts']} posts ({numbers['vs_resto']} vs. el resto)",
        numbers=numbers,
        direction="up" if (detail.lift_vs_rest or 0) >= 1 else "down",
        subject=subject,
        short=subject.removeprefix("tus "),
        lift=detail.lift_vs_rest,
        confidence=confidence_for(detail),
        related_post_ids=[p.post.id for p in members[:RELATED_POSTS]],
    )

def member_value(item: AnalyzedPost, dimension: str) -> str | None:
    """
    The value of a post for a segment or timing dimension.
    """
    block = hour_block(item.features.hour_local)
    day = day_type(item.features.weekday)
    timing: dict[str, Callable[[], str]] = {
        "hour_block": lambda: block,
        "day_type": lambda: day,
        "hour_block_day_type": lambda: f"{block}, {day}",
    }
    if dimension in timing:
        return timing[dimension]()
    return segment_value(item, SegmentDimension(dimension))

def subject_for(dimension: str, value: str) -> str:
    """
    es-AR noun phrase for the posts of a segment, e.g. ("media_type", "video") -> "tus posts con video".
    """
    if dimension == "topic":
        return f"tus posts sobre {value}"
    if dimension == "media_type":
        return f"tus posts {MEDIA_SUBJECTS.get(value, value)}"
    if dimension == "length_bucket":
        return f"tus posts {LENGTH_SUBJECTS.get(value, value)}"
    if dimension == "post_kind":
        return f"tus {KIND_SUBJECTS.get(value, value)}"
    if dimension == "tone":
        return f"tus posts de tono {value}"
    if dimension == "hook":
        return f"tus posts que arrancan con {HOOK_SUBJECTS[value]}" if value in HOOK_SUBJECTS \
            else "tus posts sin un gancho claro"
    if dimension == "cta":
        return f"tus posts que piden {CTA_SUBJECTS[value]}" if value in CTA_SUBJECTS \
            else "tus posts sin llamado a la acción"
    if dimension == "hour_block":
        return f"tus posts {BLOCK_SUBJECTS.get(value, value)}"
    if dimension == "day_type":
        return f"tus posts {DAY_SUBJECTS.get(value, value)}"
    block, _, day = value.partition(", ")
    return f"tus posts {BLOCK_SUBJECTS.get(block, block)} {DAY_SUBJECTS.get(day, day)}"

def slot_item(slot: TimeSlotStat, scored: list[AnalyzedPost]) -> EvidenceItem:
    """
    Evidence item for one of the best weekday/hour slots.
    """
    hora = f"{slot.hour} h"
    mediana = fmt_x(slot.avg_score or 0)
    label = f"{WEEKDAYS_ES[slot.weekday]} a las {hora}"
    members = [p.post.id for p in scored if (p.features.weekday, p.features.hour_local) == (slot.weekday, slot.hour)]
    return EvidenceItem(
        id=f"slot:{slot.weekday}:{slot.hour}",
        kind="slot",
        category=InsightCategory.TIMING,
        label=label,
        value=f"{mediana} tu post típico en {slot.post_count} posts",
        numbers={"mediana": mediana, "posts": str(slot.post_count), "hora": hora},
        direction="up" if (slot.avg_score or 0) >= 1 else "down",
        subject=f"tus posts de los {label}",
        short=f"posts los {label}",
        related_post_ids=members[:RELATED_POSTS],
    )

def post_evidence(item: AnalyzedPost, rank: Literal["top", "bottom"]) -> PostEvidence:
    """
    A top/bottom post with its labels and formatted score.
    """
    features = item.features
    media = features.media_type.value if features.media_type else "text"
    return PostEvidence(
        id=item.post.id,
        rank=rank,
        score=fmt_x(item.score or 0),
        text=" ".join(item.post.text.split())[:POST_TEXT_CHARS],
        topic=features.topic,
        tone=features.tone,
        hook=features.hook,
        cta=features.cta,
        formato=VALUE_LABELS[media],
        largo=VALUE_LABELS[features.length_bucket.value],
        franja=hour_block(features.hour_local),
        dia=WEEKDAYS_ES[features.weekday],
        hora=f"{features.hour_local} h",
    )
