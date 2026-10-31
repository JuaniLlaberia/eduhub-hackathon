"""
PostSource that replays saved snapshots, plus the pre-computed reports served in DEMO_MODE.

FIXTURES_DIR holds <handle>.json (AccountSnapshot) and <handle>.report.json (AnalysisReport) files.
When it has no JSON files at all, the shared fixture snapshot and report are used instead.
"""
import asyncio
from pathlib import Path
from eduhub_shared.errors import AccountNotFoundError
from eduhub_shared.fixtures import load_report, load_snapshot
from eduhub_shared.models import AccountProfile, AccountSnapshot, AnalysisReport, Post, Trend
from eduhub_shared.models.common import normalize_handle

REPORT_SUFFIX = ".report.json"

def json_files(directory: Path) -> list[Path]:
    """
    Return the JSON files of directory sorted by name (empty when it does not exist).
    """
    return sorted(directory.glob("*.json")) if directory.is_dir() else []

def snapshot_files(directory: Path) -> list[Path]:
    """
    Return the snapshot files of directory, skipping report files.
    """
    return [p for p in json_files(directory) if not p.name.endswith(REPORT_SUFFIX)]

def report_files(directory: Path) -> list[Path]:
    """
    Return the report files of directory.
    """
    return [p for p in json_files(directory) if p.name.endswith(REPORT_SUFFIX)]

def read_snapshots(directory: Path) -> dict[str, AccountSnapshot]:
    """
    Load every snapshot of directory keyed by handle, or the shared fixture when the directory has no JSON files.
    """
    if not json_files(directory):
        snapshot = load_snapshot()
        return {snapshot.profile.handle: snapshot}
    snapshots = [AccountSnapshot.model_validate_json(p.read_text(encoding="utf-8")) for p in snapshot_files(directory)]
    return {s.profile.handle: s for s in snapshots}

def read_demo_reports(directory: Path) -> list[AnalysisReport]:
    """
    Load the pre-computed reports of directory, or the shared fixture report when the directory has no JSON files.
    """
    if not json_files(directory):
        return [load_report()]
    return [AnalysisReport.model_validate_json(p.read_text(encoding="utf-8")) for p in report_files(directory)]

async def load_demo_reports(directory: Path) -> list[AnalysisReport]:
    """
    Load the pre-computed demo reports without blocking the event loop.
    """
    return await asyncio.to_thread(read_demo_reports, directory)

class FixturePostSource:
    """
    PostSource that serves one saved AccountSnapshot per handle from a directory.
    """
    def __init__(self, directory: Path) -> None:
        """
        Serve the snapshots in directory (loaded on first use).
        """
        self._directory = directory
        self._snapshots: dict[str, AccountSnapshot] | None = None

    async def _all(self) -> dict[str, AccountSnapshot]:
        """
        Return the snapshots keyed by handle, loading them once.
        """
        if self._snapshots is None:
            self._snapshots = await asyncio.to_thread(read_snapshots, self._directory)
        return self._snapshots

    async def _get(self, handle: str) -> AccountSnapshot:
        """
        Return the snapshot of handle, raising AccountNotFoundError if there is none.
        """
        shown = handle.strip().removeprefix("@")
        try:
            key = normalize_handle(handle)
        except ValueError as error:
            raise AccountNotFoundError(f"No encontramos la cuenta @{shown}.") from error
        snapshot = (await self._all()).get(key)
        if snapshot is None:
            raise AccountNotFoundError(f"No encontramos la cuenta @{shown}.")
        return snapshot

    async def fetch_profile(self, handle: str) -> AccountProfile:
        """
        Return the saved profile of handle.
        """
        return (await self._get(handle)).profile

    async def fetch_posts(self, handle: str, limit: int) -> list[Post]:
        """
        Return up to limit saved posts of handle, newest first.
        """
        posts = (await self._get(handle)).posts
        return sorted(posts, key=lambda p: p.created_at, reverse=True)[:limit]

    async def fetch_trends(self, location: str = "Argentina") -> list[Trend]:
        """
        Return the saved trends for location, without duplicates, in snapshot order.
        """
        seen: dict[str, Trend] = {}
        for snapshot in (await self._all()).values():
            for trend in snapshot.trends:
                if trend.location == location:
                    seen.setdefault(trend.name, trend)
        return list(seen.values())
