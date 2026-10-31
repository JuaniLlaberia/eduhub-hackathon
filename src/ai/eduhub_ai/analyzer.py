"""
HybridAnalyzer: the real contract Analyzer. Deterministic features, scores and stats (every number), an LLM for
labels and texts, and template fallbacks so LLM failures degrade the texts instead of failing the analysis.
"""
import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from eduhub_ai.config import AISettings
from eduhub_ai.features import MIN_SCORABLE_POSTS, extract_deterministic, score_posts, select_scorable
from eduhub_ai.insights import build_evidence, write_texts
from eduhub_ai.labeling import label_account
from eduhub_ai.labeling.labeler import hashtag_topics
from eduhub_ai.llm.client import LLMClient
from eduhub_ai.patterns import PatternModel, adjust_confidence, effect_items, fit_from_posts
from eduhub_ai.stats import best_time_slots, build_heatmap, build_kpis, build_segments
from eduhub_shared.errors import AnalysisError, ContractError
from eduhub_shared.interfaces import ProgressCallback
from eduhub_shared.metrics import compute_rates
from eduhub_shared.models import AccountSnapshot, AnalysisReport, AnalyzedPost

ENGINE = "hybrid-v1"
REPORT_NAMESPACE = uuid.UUID("b3c8f1d2-5e47-4a9b-8c61-0d2e7f9a4b35")
NOT_ENOUGH_POSTS = f"Necesitamos al menos {MIN_SCORABLE_POSTS} posts con vistas para analizar la cuenta."
UNEXPECTED_ERROR = "No pudimos analizar la cuenta. Probá de nuevo."
logger = logging.getLogger(__name__)

def utc_now() -> datetime:
    """
    The current time in UTC.
    """
    return datetime.now(UTC)

class HybridAnalyzer:
    """
    Analyzer for one account snapshot. client=None means template mode (no LLM calls).
    """
    def __init__(self, settings: AISettings, client: LLMClient | None, clock: Callable[[], datetime] = utc_now) -> None:
        """
        Keep the settings, the LLM client (or None) and the clock used for generated_at and the report id.
        """
        self.settings = settings
        self.client = client
        self._clock = clock

    async def analyze(self, snapshot: AccountSnapshot, on_progress: ProgressCallback | None = None) -> AnalysisReport:
        """
        Analyze every post of snapshot. Raises AnalysisError (es-AR message) when there is not enough data or
        something unexpected fails; LLM failures only degrade labels and texts.
        """
        try:
            return await self._analyze(snapshot, on_progress)
        except ContractError:
            raise
        except Exception as error:
            logger.exception("analysis of @%s failed", snapshot.profile.handle)
            raise AnalysisError(UNEXPECTED_ERROR) from error

    async def _analyze(self, snapshot: AccountSnapshot, on_progress: ProgressCallback | None) -> AnalysisReport:
        """
        The pipeline: features + scores → labels → stats → pattern model → texts → report.
        """
        progress = Progress(on_progress, snapshot.profile.handle)
        await progress.step(0.10, "Leyendo tus posts")
        scorable = select_scorable(snapshot.posts, snapshot.collected_at).scorable
        if len(scorable) < MIN_SCORABLE_POSTS:
            raise AnalysisError(NOT_ENOUGH_POSTS)
        scores = score_posts(scorable)
        features = {p.id: extract_deterministic(p, snapshot.trends) for p in snapshot.posts}
        await progress.step(0.30, "Clasificando temas y estilo")
        labeling = await label_account(scorable, features, self.client, self.settings, context=snapshot.context)
        features = labeling.features if labeling.taxonomy else hashtag_topics(scorable, labeling.features)
        posts = [
            AnalyzedPost(post=p, features=features[p.id], rates=compute_rates(p.metrics), score=scores.get(p.id))
            for p in snapshot.posts
        ]
        await progress.step(0.60, "Calculando patrones")
        kpis = build_kpis(snapshot.posts)
        heatmap = build_heatmap(posts)
        slots = best_time_slots(heatmap)
        segments = build_segments(posts)
        model = self.pattern_model(posts)
        effects = effect_items(model, posts) if model is not None else []
        pack = build_evidence(snapshot.profile, kpis, posts, slots, pattern_effects=effects, context=snapshot.context)
        if model is not None:
            pack = adjust_confidence(pack, model)
        await progress.step(0.80, "Escribiendo tus insights")
        texts = await write_texts(pack, self.client, self.settings)
        for error in [*labeling.errors, *texts.errors]:
            logger.warning("@%s degraded: %s", snapshot.profile.handle, error)
        generated_at = self._clock()
        report = AnalysisReport(
            id=str(uuid.uuid5(REPORT_NAMESPACE, f"{ENGINE}|{snapshot.profile.handle}|{generated_at.isoformat()}")),
            profile=snapshot.profile,
            generated_at=generated_at,
            kpis=kpis,
            posts=[p.model_copy(update={"explanation": texts.explanations.get(p.post.id)}) for p in posts],
            heatmap=heatmap,
            segments=segments,
            best_time_slots=slots,
            insights=texts.insights,
            recommendations=texts.recommendations,
            summary=texts.summary,
            engine=ENGINE,
            context=snapshot.context,
        )
        await progress.step(1.0, "Análisis listo")
        logger.info("@%s analyzed: labels %.0f%%, texts from %s", snapshot.profile.handle,
                    labeling.coverage * 100, texts.source)
        return report

    def pattern_model(self, posts: list[AnalyzedPost]) -> PatternModel | None:
        """
        The per-account ridge model, or None when the account lacks data for it (fewer than 30 scorable posts
        or no usable feature). Model failures never fail the analysis.
        """
        try:
            return fit_from_posts(posts)
        except (ValueError, ArithmeticError) as error:
            logger.warning("pattern model skipped: %s", error)
            return None

class Progress:
    """
    Reports progress to the backend and logs how long each step took.
    """
    def __init__(self, callback: ProgressCallback | None, handle: str) -> None:
        """
        Keep the optional callback and start the step timer.
        """
        self._callback = callback
        self._handle = handle
        self._started = time.perf_counter()
        self._last: str | None = None

    async def step(self, value: float, message: str) -> None:
        """
        Log the time spent on the previous step and report the new one.
        """
        now = time.perf_counter()
        if self._last is not None:
            logger.info("@%s step '%s' took %.2fs", self._handle, self._last, now - self._started)
        self._started, self._last = now, message
        if self._callback is not None:
            await self._callback(value, message)
