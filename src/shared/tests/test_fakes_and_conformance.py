from datetime import UTC, datetime
import pytest
from eduhub_shared.errors import AccountNotFoundError, AnalysisError
from eduhub_shared.fakes import (
    FakeAnalyzer,
    FakeAudienceSimulator,
    FakeDraftGenerator,
    FakePostPublisher,
    FakePostSource,
    next_slot_after,
)
from eduhub_shared.fixtures import load_report, load_snapshot
from eduhub_shared.interfaces import Analyzer, AudienceSimulator, DraftGenerator, PostPublisher, PostSource
from eduhub_shared.models import PublishRequest, PublishStatus
from eduhub_shared.routes import ROUTES
from eduhub_shared.testing import (
    assert_report_matches_snapshot,
    assert_routes_match_contract,
    check_analyzer,
    check_generator,
    check_post_source,
    check_simulator,
)

def test_fakes_implement_the_interfaces():
    assert isinstance(FakePostSource(), PostSource)
    assert isinstance(FakePostPublisher(), PostPublisher)
    assert isinstance(FakeAnalyzer(), Analyzer)
    assert isinstance(FakeDraftGenerator(), DraftGenerator)
    assert isinstance(FakeAudienceSimulator(), AudienceSimulator)

async def test_fake_analyzer_passes_the_conformance_check():
    report = await check_analyzer(FakeAnalyzer())
    assert report.engine == "fake"
    assert report.insights and report.recommendations

async def test_fake_analyzer_rejects_empty_accounts():
    snapshot = load_snapshot().model_copy(update={"posts": []})
    with pytest.raises(AnalysisError):
        await FakeAnalyzer().analyze(snapshot)

def test_fixture_report_matches_fixture_snapshot():
    assert_report_matches_snapshot(load_report(), load_snapshot())

async def test_fake_generator_passes_the_conformance_check():
    await check_generator(FakeDraftGenerator(), count=4)

async def test_fake_simulator_passes_the_conformance_check():
    await check_simulator(FakeAudienceSimulator())

async def test_fake_source_passes_the_conformance_check():
    snapshot = await check_post_source(FakePostSource(), "@demo_finanzas", limit=10)
    assert len(snapshot.posts) == 10

async def test_fake_source_rejects_unknown_accounts():
    with pytest.raises(AccountNotFoundError):
        await FakePostSource().fetch_profile("someone_else")

async def test_fake_publisher_returns_intent_or_schedule():
    now = await FakePostPublisher().publish(PublishRequest(handle="demo", text="hola mundo"))
    assert now.status == PublishStatus.INTENT and now.url.startswith("https://x.com/intent/post?text=hola")
    later = datetime(2026, 11, 2, 0, 0, tzinfo=UTC)
    scheduled = await FakePostPublisher().publish(PublishRequest(handle="demo", text="hola", scheduled_for=later))
    assert scheduled.status == PublishStatus.SCHEDULED and scheduled.scheduled_for == later

def test_next_slot_is_in_the_future_and_on_the_right_local_slot():
    moment = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
    slot = next_slot_after(moment, weekday=2, hour=21)
    assert slot > moment
    assert slot.isoformat() == "2026-11-05T00:00:00+00:00"

def test_route_check_accepts_the_contract_and_rejects_drift():
    contract = [(r.method, r.path) for r in ROUTES]
    assert_routes_match_contract([*contract, ("GET", "/docs"), ("HEAD", "/health")])
    with pytest.raises(AssertionError, match="missing"):
        assert_routes_match_contract(contract[1:])
    with pytest.raises(AssertionError, match="not in the contract"):
        assert_routes_match_contract([*contract, ("GET", "/secret")])
    assert_routes_match_contract([*contract, ("GET", "/secret")], allow_extra=["/secret"])
