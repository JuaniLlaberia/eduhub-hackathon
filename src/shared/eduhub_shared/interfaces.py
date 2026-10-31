"""
Contracts C2 and C3: Python interfaces between backend and AI.

Implementations raise the exceptions in eduhub_shared.errors; anything else is treated as an internal error.
The AI package must export: create_analyzer() -> Analyzer, create_generator() -> DraftGenerator,
create_simulator() -> AudienceSimulator | None (None = feature disabled).
"""
from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable
from eduhub_shared.models import (
    AccountProfile,
    AccountSnapshot,
    AnalysisReport,
    Draft,
    DraftRequest,
    Post,
    PublishRequest,
    PublishResult,
    SimulationRequest,
    SimulationResult,
    Trend,
)

ProgressCallback = Callable[[float, str], Awaitable[None]]
"""Called with (progress 0..1, es-AR step label)."""

@runtime_checkable
class PostSource(Protocol):
    """
    Fetches normalized account data. Implemented by the backend (twitterapi.io, scraper, fixture...).
    """
    async def fetch_profile(self, handle: str) -> AccountProfile:
        """
        Return the profile of handle. Raise AccountNotFoundError if it does not exist.
        """
        ...

    async def fetch_posts(self, handle: str, limit: int) -> list[Post]:
        """
        Return up to limit of the account's most recent posts, newest first.
        """
        ...

    async def fetch_trends(self, location: str = "Argentina") -> list[Trend]:
        """
        Return the current trends for location (may be empty).
        """
        ...

@runtime_checkable
class PostPublisher(Protocol):
    """
    Publishes or schedules posts. Implemented by the backend.
    """
    async def publish(self, request: PublishRequest) -> PublishResult:
        """
        Publish or schedule request.text. Failures are reported with status FAILED, not raised.
        """
        ...

@runtime_checkable
class Analyzer(Protocol):
    """
    Turns an AccountSnapshot into an AnalysisReport. Implemented by the AI team.
    """
    async def analyze(self, snapshot: AccountSnapshot, on_progress: ProgressCallback | None = None) -> AnalysisReport:
        """
        Analyze every post in snapshot and return the report. Raise AnalysisError on failure.
        """
        ...

@runtime_checkable
class DraftGenerator(Protocol):
    """
    Generates drafts in the creator's voice. Implemented by the AI team.
    """
    async def generate(self, request: DraftRequest, report: AnalysisReport, trends: list[Trend]) -> list[Draft]:
        """
        Return request.count drafts. Raise GenerationError on failure.
        """
        ...

@runtime_checkable
class AudienceSimulator(Protocol):
    """
    Simulates synthetic audience reactions to text variants. Implemented by the AI team (stretch).
    """
    async def simulate(self, request: SimulationRequest) -> SimulationResult:
        """
        Return reactions for every variant. Raise SimulationError on failure.
        """
        ...
