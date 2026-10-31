"""
Build every fixture deterministically from a fictional creator account and the fake implementations.

Usage: python -m eduhub_shared.fixtures.build            (write the files)
       python -m eduhub_shared.fixtures.build --check    (exit 1 if committed fixtures are outdated)
"""
import asyncio
import random
import sys
from datetime import UTC, datetime, timedelta
from pydantic import BaseModel
from eduhub_shared.fakes import AR_TZ, FakeAnalyzer, FakeAudienceSimulator, FakeDraftGenerator, FakePostPublisher
from eduhub_shared.fixtures import FIXTURES_DIR
from eduhub_shared.models import (
    AccountProfile,
    AccountSnapshot,
    AnalysisJob,
    ApiError,
    AudienceFilters,
    CreatorContext,
    CreatorGoal,
    DraftRequest,
    DraftsResponse,
    ErrorCode,
    ErrorResponse,
    FeatureFlags,
    HealthResponse,
    JobStatus,
    MediaType,
    Post,
    PostKind,
    PostMetrics,
    PreferredCta,
    PublishRequest,
    SimulationRequest,
    Trend,
    TrendsResponse,
)
from eduhub_shared.version import CONTRACT_VERSION

HANDLE = "demo_finanzas"
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
TEXTS = {
    "presupuesto": (
        "El método 50/30/20 adaptado a Argentina: 50% fijos, 30% vida, 20% a ahorro en lo que no se licúa.",
        "Mi planilla de presupuesto mensual, gratis. Guardala y usala el día que cobrás 📊",
        "Presupuesto en 3 pasos: anotá todo una semana, separá fijos de variables, recortá lo que no te suma.",
        "¿Llevás un presupuesto mensual? Contame qué app o método usás 👇",
        "Si no sabés a dónde se va tu sueldo, no es falta de plata: es falta de registro.",
        "Checklist de fin de mes: revisar gastos hormiga, suscripciones que no usás y cuotas que vencen 🧾",
        "La regla de las 48 horas: antes de cualquier compra no planificada, esperá dos días. Te sorprende.",
        "Infografía: cómo armar tu primer presupuesto si cobrás en negro o por proyecto.",
    ),
    "ahorro": (
        "Ahorrar no es lo que sobra a fin de mes. Es lo primero que separás cuando cobrás.",
        "¿Cuánto de tu sueldo lográs ahorrar? Sin juzgar, quiero saber la realidad 👀",
        "Fondo de emergencia: 3 a 6 meses de gastos fijos. Empezá con uno, aunque tardes.",
        "Mi truco para ahorrar: una cuenta separada que no veo en la app del banco.",
        "Ahorrar en pesos vs. en dólares: lo que nadie te explica de la inflación y el plazo.",
        "5 gastos hormiga que me comían 30 mil pesos por mes y cómo los corté 🐜",
        "Ahorro automático: programá la transferencia para el día de cobro y olvidate.",
        "¡Llegué a mi primer fondo de emergencia completo! Les cuento cómo lo hice en un hilo 🧵",
    ),
    "inversiones": (
        "Plazo fijo, FCI o cuenta remunerada: diferencias explicadas en 1 minuto.",
        "¿Empezaste a invertir este año? ¿En qué? Leo todo 👇",
        "Antes de invertir: fondo de emergencia, deudas al día y objetivos claros. En ese orden.",
        "Qué es un FCI money market y por qué lo uso para la plata del mes.",
        "Diversificar no es tener 20 activos. Es no depender de uno solo.",
        "Hilo: cómo leer el rendimiento de una inversión sin marearte con los porcentajes 🧵",
        "La mejor inversión del año fue un curso de finanzas de 10 mil pesos. En serio.",
        "Interés compuesto explicado con un mate: un ejemplo simple que te va a cambiar la cabeza.",
    ),
    "sueldo": (
        "Cobraste el aguinaldo. Antes de gastarlo, pensá en estos 3 destinos.",
        "¿Negociaste tu sueldo alguna vez? Cuento cómo me fue la primera vez.",
        "Recibo de sueldo: qué es cada descuento y por qué te importa.",
        "Freelance y cobrás en dólares: tres cosas que tenés que ordenar sí o sí.",
        "Si tu sueldo aumenta y tu ahorro no, el problema no es el sueldo.",
        "¿Cuánto tiempo te dura el sueldo? Encuesta honesta 👇",
        "Aumento de sueldo: subí el ahorro antes de subir el estilo de vida.",
        "Primer sueldo: la guía que me hubiera gustado leer a los 20.",
    ),
    "tarjetas": (
        "Pagar el mínimo de la tarjeta es la deuda más cara que podés tener.",
        "Cuotas sin interés: cuándo convienen y cuándo son una trampa.",
        "¿Usás la tarjeta de crédito o la evitás? Debate.",
        "Resumen de tarjeta: las 4 líneas que tenés que mirar siempre.",
        "Cómo salí de la deuda de la tarjeta en 8 meses, paso a paso.",
        "Tarjeta de débito vs. crédito para el día a día.",
        "Fecha de cierre y vencimiento: el truco para ganar casi 50 días de financiación.",
        "Error de novato con la tarjeta: confundir límite de compra con plata disponible.",
    ),
}
TOPIC_FACTOR = {"presupuesto": 1.6, "ahorro": 1.25, "inversiones": 1.0, "sueldo": 0.9, "tarjetas": 0.6}
SLOTS = ((21, 1.5), (8, 1.1), (15, 0.75), (21, 1.5), (13, 0.85))
WEEKEND_FACTOR = 0.85
FOLLOWERS = 18400

def build_post(index: int, rng: random.Random) -> Post:
    """
    Build one fictional post with metrics shaped by topic, time slot, media and question factors.
    """
    topic = tuple(TEXTS)[index % len(TEXTS)]
    text = TEXTS[topic][index // len(TEXTS)]
    hour, time_factor = SLOTS[index % len(SLOTS)]
    day = NOW.astimezone(AR_TZ) - timedelta(days=round((40 - index) * 1.75))
    local = day.replace(hour=hour, minute=rng.choice((0, 5, 12, 30, 45)), second=0, microsecond=0)
    if local.weekday() >= 5:
        time_factor *= WEEKEND_FACTOR
    is_photo = "infograf" in text.lower() or "planilla" in text.lower() or index % 6 == 0
    is_question = "?" in text
    factor = TOPIC_FACTOR[topic] * time_factor * rng.uniform(0.8, 1.2)
    impressions = int(FOLLOWERS * 0.15 * factor * rng.uniform(0.85, 1.15))
    media_boost = 1.3 if is_photo else 1.0
    metrics = PostMetrics(
        impressions=impressions,
        likes=int(impressions * 0.018 * factor * media_boost),
        reposts=int(impressions * 0.003 * factor),
        quotes=int(impressions * 0.0006 * factor),
        replies=int(impressions * 0.0025 * factor * (3.0 if is_question else 1.0)),
        bookmarks=int(impressions * 0.004 * factor * (1.6 if is_photo else 1.0)),
    )
    post_id = str(1980000000000000000 + index * 7919)
    return Post(
        id=post_id,
        author_handle=HANDLE,
        text=f"{text} #{topic}",
        created_at=local.astimezone(UTC),
        url=f"https://x.com/{HANDLE}/status/{post_id}",
        lang="es",
        kind=PostKind.ORIGINAL,
        media=[MediaType.PHOTO] if is_photo else [],
        hashtags=[topic],
        conversation_id=post_id if "🧵" in text else None,
        metrics=metrics,
    )

EXAMPLE_CONTEXT = CreatorContext(
    goal=CreatorGoal.SELL,
    goal_detail="Llenar la próxima cohorte del curso antes de fin de mes.",
    offering="Curso online de finanzas personales para gente que cobra en pesos (4 semanas).",
    target_audience="Jóvenes que empiezan a trabajar y no saben cómo organizar su sueldo.",
    audience_filters=AudienceFilters(age_groups=["18 a 29 años", "30 a 49 años"]),
    brand_voice="Cercana, con humor y sin tecnicismos. Siempre con voseo.",
    avoid_topics=["política", "cripto"],
    preferred_cta=PreferredCta.LINK,
)

def build_snapshot() -> AccountSnapshot:
    """
    Build the fictional account snapshot (40 posts over ~10 weeks, newest first).
    """
    rng = random.Random(2026)
    posts = sorted((build_post(i, rng) for i in range(40)), key=lambda p: p.created_at, reverse=True)
    profile = AccountProfile(
        handle=HANDLE,
        display_name="Cami (demo) · Finanzas sin vueltas",
        bio="Cuenta ficticia de ejemplo. Finanzas personales para gente que cobra en pesos 💸",
        followers_count=FOLLOWERS,
        following_count=612,
        posts_count=2140,
        created_at=datetime(2021, 3, 14, 15, 0, tzinfo=UTC),
    )
    trends = [
        Trend(name=name, rank=rank, post_count=count, observed_at=NOW)
        for rank, (name, count) in enumerate(
            (("#Aguinaldo", 48200), ("Halloween", 31000), ("#FinanzasPersonales", 12800), ("Black Friday", 9600)),
            start=1,
        )
    ]
    return AccountSnapshot(profile=profile, posts=posts, trends=trends, source="fixture", collected_at=NOW,
                           context=EXAMPLE_CONTEXT)

def job(status: JobStatus, progress: float, message: str | None, report_id: str | None = None,
        error: ApiError | None = None) -> AnalysisJob:
    """
    Build an example analysis job in the given state.
    """
    return AnalysisJob(
        id="job-demo-1", handle=HANDLE, status=status, progress=progress, message=message,
        created_at=NOW, updated_at=NOW + timedelta(seconds=int(progress * 40)), report_id=report_id, error=error,
    )

def clock() -> datetime:
    """
    Fixed clock used for every generated fixture.
    """
    return NOW + timedelta(minutes=1)

async def build_all() -> dict[str, BaseModel]:
    """
    Build every fixture model, keyed by file name.
    """
    snapshot = build_snapshot()
    report = await FakeAnalyzer(clock=clock).analyze(snapshot)
    drafts = await FakeDraftGenerator(clock=clock).generate(DraftRequest(handle=HANDLE), report, snapshot.trends)
    simulation = await FakeAudienceSimulator(clock=clock).simulate(SimulationRequest(
        handle=HANDLE, audience_size=24, variants=[drafts[0].text, drafts[1].text],
    ))
    published = await FakePostPublisher().publish(PublishRequest(handle=HANDLE, text=drafts[0].text))
    return {
        "account_snapshot.json": snapshot,
        "analysis_report.json": report,
        "analysis_job_queued.json": job(JobStatus.QUEUED, 0.0, "En cola"),
        "analysis_job_analyzing.json": job(JobStatus.ANALYZING, 0.6, "Calculando métricas y patrones"),
        "analysis_job_done.json": job(JobStatus.DONE, 1.0, "Listo", report_id=report.id),
        "analysis_job_failed.json": job(JobStatus.FAILED, 0.2, None, error=ApiError(
            code=ErrorCode.SOURCE_UNAVAILABLE, message="No pudimos obtener los posts. Probá de nuevo en unos minutos.",
        )),
        "drafts_response.json": DraftsResponse(drafts=drafts),
        "publish_result.json": published,
        "simulation_result.json": simulation,
        "feature_flags.json": FeatureFlags(generation=True, publishing=True, simulation=False, demo_mode=False),
        "health.json": HealthResponse(contract_version=CONTRACT_VERSION),
        "trends_response.json": TrendsResponse(trends=snapshot.trends),
        "error_not_found.json": ErrorResponse(error=ApiError(
            code=ErrorCode.NOT_FOUND, message="No encontramos lo que buscabas.",
        )),
    }

def render(model: BaseModel) -> str:
    """
    Serialize a fixture model deterministically.
    """
    return model.model_dump_json(indent=2) + "\n"

def main() -> None:
    """
    Write all fixtures, or verify they are up to date with --check.
    """
    fixtures = asyncio.run(build_all())
    outdated = []
    for name, model in fixtures.items():
        path = FIXTURES_DIR / name
        rendered = render(model)
        if "--check" in sys.argv:
            if not path.exists() or path.read_text(encoding="utf-8") != rendered:
                outdated.append(name)
            continue
        path.write_text(rendered, encoding="utf-8")
    if outdated:
        print(f"outdated fixtures: {outdated}. Run `python -m eduhub_shared.fixtures.build`", file=sys.stderr)
        sys.exit(1)
    print("fixtures are up to date" if "--check" in sys.argv else f"wrote {len(fixtures)} fixtures to {FIXTURES_DIR}")

if __name__ == "__main__":
    main()
