"""
Persistence for analysis jobs, snapshots and reports. Models are stored as JSON documents in SQLite.
"""
from pathlib import Path
from typing import Protocol
import aiosqlite
from eduhub_shared.models import AccountSnapshot, AnalysisJob, AnalysisReport

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    handle TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reports (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    handle TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS reports_by_handle ON reports (handle, seq);
"""

class Store(Protocol):
    """
    Storage used by the job runner and the API.
    """
    async def init(self) -> None:
        """
        Open the storage and create its schema if needed.
        """
        ...

    async def close(self) -> None:
        """
        Release the storage.
        """
        ...

    async def save_job(self, job: AnalysisJob) -> None:
        """
        Insert or replace job.
        """
        ...

    async def get_job(self, job_id: str) -> AnalysisJob | None:
        """
        Return the job with job_id, or None.
        """
        ...

    async def save_snapshot(self, snapshot: AccountSnapshot) -> None:
        """
        Store the snapshot an analysis was run on.
        """
        ...

    async def save_report(self, report: AnalysisReport) -> None:
        """
        Store report; saving it again makes it the latest report of its account.
        """
        ...

    async def get_report(self, report_id: str) -> AnalysisReport | None:
        """
        Return the report with report_id, or None.
        """
        ...

    async def get_latest_report(self, handle: str) -> AnalysisReport | None:
        """
        Return the most recently stored report of handle, or None.
        """
        ...

class SqliteStore:
    """
    Store backed by a SQLite file through aiosqlite.
    """
    def __init__(self, path: Path) -> None:
        """
        Use the SQLite database at path (created on init).
        """
        self._path = path
        self._db: aiosqlite.Connection | None = None

    @property
    def db(self) -> aiosqlite.Connection:
        """
        Return the open connection, failing clearly if init was not called.
        """
        if self._db is None:
            raise RuntimeError("SqliteStore.init() must be called first")
        return self._db

    async def init(self) -> None:
        """
        Create parent directories, open the database and create the schema.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        """
        Close the connection if open.
        """
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def _write(self, sql: str, params: tuple[str, ...]) -> None:
        """
        Execute a write statement and commit it.
        """
        await self.db.execute(sql, params)
        await self.db.commit()

    async def _read_one(self, sql: str, params: tuple[str, ...]) -> str | None:
        """
        Return the data column of the first row of a query, or None.
        """
        async with self.db.execute(sql, params) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None

    async def save_job(self, job: AnalysisJob) -> None:
        """
        Insert or replace job.
        """
        await self._write("INSERT OR REPLACE INTO jobs (id, data) VALUES (?, ?)", (job.id, job.model_dump_json()))

    async def get_job(self, job_id: str) -> AnalysisJob | None:
        """
        Return the job with job_id, or None.
        """
        data = await self._read_one("SELECT data FROM jobs WHERE id = ?", (job_id,))
        return AnalysisJob.model_validate_json(data) if data else None

    async def save_snapshot(self, snapshot: AccountSnapshot) -> None:
        """
        Store the snapshot an analysis was run on.
        """
        sql = "INSERT INTO snapshots (handle, data) VALUES (?, ?)"
        await self._write(sql, (snapshot.profile.handle, snapshot.model_dump_json()))

    async def save_report(self, report: AnalysisReport) -> None:
        """
        Store report; INSERT OR REPLACE gives it a new seq, so it becomes the latest of its account.
        """
        sql = "INSERT OR REPLACE INTO reports (id, handle, data) VALUES (?, ?, ?)"
        await self._write(sql, (report.id, report.profile.handle, report.model_dump_json()))

    async def get_report(self, report_id: str) -> AnalysisReport | None:
        """
        Return the report with report_id, or None.
        """
        data = await self._read_one("SELECT data FROM reports WHERE id = ?", (report_id,))
        return AnalysisReport.model_validate_json(data) if data else None

    async def get_latest_report(self, handle: str) -> AnalysisReport | None:
        """
        Return the most recently stored report of handle, or None.
        """
        sql = "SELECT data FROM reports WHERE handle = ? ORDER BY seq DESC LIMIT 1"
        data = await self._read_one(sql, (handle,))
        return AnalysisReport.model_validate_json(data) if data else None
