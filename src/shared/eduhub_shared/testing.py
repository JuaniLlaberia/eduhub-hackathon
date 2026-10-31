"""
Contract conformance helpers. Each team calls these from its own tests to prove it honours the contracts.

- Back:  assert_routes_match_contract(fastapi_routes(app)); await check_post_source(source, handle)
- AI:    await check_analyzer(create_analyzer()); await check_generator(...); await check_simulator(...)
"""
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from eduhub_shared.fixtures import load_report, load_snapshot
from eduhub_shared.interfaces import Analyzer, AudienceSimulator, DraftGenerator, PostSource
from eduhub_shared.metrics import compute_rates
from eduhub_shared.models import (
    AccountProfile,
    AccountSnapshot,
    AnalysisReport,
    Draft,
    DraftRequest,
    Post,
    SimulationRequest,
    SimulationResult,
)
from eduhub_shared.routes import ROUTES

IGNORED_PATHS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
IGNORED_METHODS = {"HEAD", "OPTIONS"}
RATE_TOLERANCE = 1e-9

def assert_report_matches_snapshot(report: AnalysisReport, snapshot: AccountSnapshot) -> None:
    """
    Assert the invariants every AnalysisReport must satisfy for the snapshot it was built from.
    """
    snapshot_ids = [p.id for p in snapshot.posts]
    report_ids = [p.post.id for p in report.posts]
    assert report_ids == snapshot_ids, "report.posts must contain every snapshot post exactly once, same order"
    assert report.profile.handle == snapshot.profile.handle, "report.profile must be the snapshot profile"
    for item in report.posts:
        expected = compute_rates(item.post.metrics)
        for name, value in expected.model_dump().items():
            actual = getattr(item.rates, name)
            assert (value is None) == (actual is None), f"rate {name} of post {item.post.id} must use metrics.py"
            if value is not None:
                assert abs(actual - value) < RATE_TOLERANCE, f"rate {name} of post {item.post.id} must use metrics.py"
    slots = {(s.weekday, s.hour) for s in report.heatmap}
    assert len(slots) == len(report.heatmap), "heatmap slots must be unique"
    assert all((s.weekday, s.hour) in slots for s in report.best_time_slots), "best slots must be heatmap slots"
    insight_ids = {i.id for i in report.insights}
    assert len(insight_ids) == len(report.insights), "insight ids must be unique"
    known_posts = set(snapshot_ids)
    for insight in report.insights:
        assert set(insight.related_post_ids) <= known_posts, f"insight {insight.id} references unknown posts"
    for rec in report.recommendations:
        assert set(rec.based_on_insight_ids) <= insight_ids, f"recommendation {rec.id} references unknown insights"
    assert report.summary.strip(), "summary must not be empty"
    assert report.engine.strip(), "engine must be set"

async def check_analyzer(analyzer: Analyzer, snapshot: AccountSnapshot | None = None) -> AnalysisReport:
    """
    Run analyzer on snapshot (default: fixture) and assert the report honours the contract.
    """
    assert isinstance(analyzer, Analyzer), "must implement eduhub_shared.interfaces.Analyzer"
    snapshot = snapshot or load_snapshot()
    progress: list[float] = []

    async def on_progress(value: float, message: str) -> None:
        """
        Record progress values and check their range.
        """
        assert 0 <= value <= 1 and message
        progress.append(value)

    report = await analyzer.analyze(snapshot, on_progress)
    assert isinstance(report, AnalysisReport)
    AnalysisReport.model_validate(report.model_dump())
    assert progress == sorted(progress), "progress must not go backwards"
    assert_report_matches_snapshot(report, snapshot)
    return report

async def check_generator(generator: DraftGenerator, count: int = 3) -> list[Draft]:
    """
    Run generator against the fixture report and assert it returns count valid drafts.
    """
    assert isinstance(generator, DraftGenerator), "must implement eduhub_shared.interfaces.DraftGenerator"
    report = load_report()
    request = DraftRequest(handle=report.profile.handle, count=count)
    drafts = await generator.generate(request, report, load_snapshot().trends)
    assert len(drafts) == count, "must return exactly request.count drafts"
    assert all(isinstance(d, Draft) for d in drafts)
    assert len({d.id for d in drafts}) == count, "draft ids must be unique"
    insight_ids = {i.id for i in report.insights}
    assert all(set(d.based_on_insight_ids) <= insight_ids for d in drafts), "drafts reference unknown insights"
    return drafts

async def check_simulator(simulator: AudienceSimulator, variants: list[str] | None = None) -> SimulationResult:
    """
    Run simulator on example variants and assert the result honours the contract.
    """
    assert isinstance(simulator, AudienceSimulator), "must implement eduhub_shared.interfaces.AudienceSimulator"
    variants = variants or ["¿Llevás un presupuesto mensual?", "Mi planilla de presupuesto, gratis 📊"]
    result = await simulator.simulate(SimulationRequest(variants=variants, audience_size=10))
    assert isinstance(result, SimulationResult)
    assert [v.variant_index for v in result.variants] == list(range(len(variants)))
    persona_ids = {p.id for p in result.personas}
    assert all(r.persona_id in persona_ids for r in result.reactions), "reactions reference unknown personas"
    assert all(0 <= r.variant_index < len(variants) for r in result.reactions)
    assert 0 <= result.best_variant_index < len(variants)
    assert result.disclaimer.strip(), "a disclaimer is required"
    return result

async def check_post_source(source: PostSource, handle: str, limit: int = 20) -> AccountSnapshot:
    """
    Fetch an account through source, assert the data honours the contract and return it as a snapshot.
    """
    assert isinstance(source, PostSource), "must implement eduhub_shared.interfaces.PostSource"
    profile = await source.fetch_profile(handle)
    posts = await source.fetch_posts(handle, limit)
    trends = await source.fetch_trends()
    assert isinstance(profile, AccountProfile)
    assert len(posts) <= limit, "must not return more than limit posts"
    assert all(isinstance(p, Post) for p in posts)
    assert [p.created_at for p in posts] == sorted((p.created_at for p in posts), reverse=True), "newest first"
    assert len({p.id for p in posts}) == len(posts), "post ids must be unique"
    return AccountSnapshot(profile=profile, posts=posts, trends=trends, source="check", collected_at=datetime.now(UTC))

def fastapi_routes(app: Any) -> list[tuple[str, str]]:
    """
    Extract (METHOD, path) pairs from a FastAPI/Starlette app without importing FastAPI.
    """
    pairs = []
    for route in getattr(app, "routes", []):
        for method in getattr(route, "methods", None) or ():
            pairs.append((method.upper(), route.path))
    return pairs

def assert_routes_match_contract(routes: Iterable[tuple[str, str]], allow_extra: Iterable[str] = ()) -> None:
    """
    Assert the app exposes exactly the contract routes (plus docs routes and paths listed in allow_extra).
    """
    actual = {(m, p) for m, p in routes if m not in IGNORED_METHODS and p not in IGNORED_PATHS}
    expected = {(r.method, r.path) for r in ROUTES}
    missing = expected - actual
    extra = {(m, p) for m, p in actual - expected if p not in set(allow_extra)}
    assert not missing, f"missing contract routes: {sorted(missing)}"
    assert not extra, f"routes not in the contract: {sorted(extra)} (propose a contract change)"
