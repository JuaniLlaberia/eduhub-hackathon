"""
Analysis job runner: queued -> fetching -> analyzing -> done | failed, as asyncio tasks.
"""
import asyncio
import logging
from datetime import UTC, datetime
from uuid import uuid4
from eduhub_backend.errors import api_error_from
from eduhub_backend.storage import Store
from eduhub_shared.interfaces import Analyzer, PostSource
from eduhub_shared.models import (
    AccountProfile,
    AccountSnapshot,
    AnalysisJob,
    AnalysisReport,
    AnalysisRequest,
    JobStatus,
)

logger = logging.getLogger(__name__)

FETCH_PROGRESS = 0.05
ANALYZE_START = 0.1
ANALYZE_END = 0.99
QUEUED_MESSAGE = "En cola"
FETCHING_MESSAGE = "Descargando los posts de la cuenta"
ANALYZING_MESSAGE = "Analizando los posts"
DONE_MESSAGE = "Análisis listo"
FAILED_MESSAGE = "El análisis falló"

def utc_now() -> datetime:
    """
    Return the current time in UTC.
    """
    return datetime.now(UTC)

class JobRunner:
    """
    Starts analysis jobs in the background and records their progress in the store.
    """
    def __init__(self, store: Store, source: PostSource, analyzer: Analyzer) -> None:
        """
        Run jobs with source and analyzer, persisting them in store.
        """
        self._store = store
        self._source = source
        self._analyzer = analyzer
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._latest: dict[str, AnalysisJob] = {}

    async def start(self, request: AnalysisRequest, profile: AccountProfile) -> AnalysisJob:
        """
        Store a queued job for an already fetched profile and run it in the background.
        """
        now = utc_now()
        job = AnalysisJob(
            id=uuid4().hex, handle=profile.handle, status=JobStatus.QUEUED, progress=0,
            message=QUEUED_MESSAGE, created_at=now, updated_at=now,
        )
        await self._store.save_job(job)
        self._tasks[job.id] = asyncio.create_task(self._run(job, request, profile))
        return job

    async def wait(self, job_id: str) -> None:
        """
        Wait until the job with job_id has finished (no-op for unknown jobs).
        """
        task = self._tasks.get(job_id)
        if task is not None:
            await asyncio.gather(task, return_exceptions=True)

    async def wait_all(self) -> None:
        """
        Wait until every started job has finished.
        """
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)

    async def _update(self, job_id: str, **changes: object) -> None:
        """
        Store the running job with changes applied and a fresh updated_at, keeping progress monotonic.
        """
        job = self._latest[job_id]
        if "progress" in changes:
            changes["progress"] = max(job.progress, float(changes["progress"]))
        self._latest[job_id] = job.model_copy(update={**changes, "updated_at": utc_now()})
        await self._store.save_job(self._latest[job_id])

    async def _run(self, job: AnalysisJob, request: AnalysisRequest, profile: AccountProfile) -> None:
        """
        Fetch, analyze and store the report, recording failures on the job instead of raising.
        """
        self._latest[job.id] = job
        try:
            await self._update(job.id, status=JobStatus.FETCHING, progress=FETCH_PROGRESS, message=FETCHING_MESSAGE)
            snapshot = await self._fetch(profile, request.max_posts)
            await self._update(job.id, status=JobStatus.ANALYZING, progress=ANALYZE_START, message=ANALYZING_MESSAGE)
            report = await self._analyze(job.id, snapshot)
            await self._store.save_report(report)
            await self._update(job.id, status=JobStatus.DONE, progress=1.0, message=DONE_MESSAGE, report_id=report.id)
        except Exception as error:
            logger.exception("analysis job %s failed", job.id)
            await self._update(job.id, status=JobStatus.FAILED, message=FAILED_MESSAGE, error=api_error_from(error))
        finally:
            self._tasks.pop(job.id, None)
            self._latest.pop(job.id, None)

    async def _fetch(self, profile: AccountProfile, limit: int) -> AccountSnapshot:
        """
        Fetch posts and trends for profile and store them as a snapshot.
        """
        posts = await self._source.fetch_posts(profile.handle, limit)
        trends = await self._source.fetch_trends()
        snapshot = AccountSnapshot(
            profile=profile, posts=posts, trends=trends, source=type(self._source).__name__, collected_at=utc_now()
        )
        await self._store.save_snapshot(snapshot)
        return snapshot

    async def _analyze(self, job_id: str, snapshot: AccountSnapshot) -> AnalysisReport:
        """
        Run the analyzer, mapping its 0..1 progress into the analyzing range of the job.
        """
        async def on_progress(value: float, message: str) -> None:
            """
            Record the analyzer's progress and step label on the job.
            """
            progress = ANALYZE_START + (ANALYZE_END - ANALYZE_START) * min(max(value, 0.0), 1.0)
            await self._update(job_id, progress=progress, message=message)

        return await self._analyzer.analyze(snapshot, on_progress)
