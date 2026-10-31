import json
from datetime import UTC, datetime, timedelta
import httpx
import pytest
from conftest import DEMO_HANDLE, snapshot_for, write_snapshot
from test_twitterapi_io_source import FakeApi
from eduhub_backend.sources.fixture import FixturePostSource, read_demo_reports
from eduhub_backend.sources.twitterapi_io import TwitterApiIoSource
from eduhub_backend.tools.snapshot import build_snapshot, run, write_fixture, write_shared
from eduhub_shared.fakes import FakeAnalyzer
from eduhub_shared.fixtures import load_report, load_snapshot
from eduhub_shared.models import AccountSnapshot, AnalysisReport
from eduhub_shared.testing import assert_report_matches_snapshot, check_post_source

@pytest.fixture
def shared_source(tmp_path):
    return FixturePostSource(tmp_path / "empty")

@pytest.fixture
def out(tmp_path):
    return tmp_path / "out"

async def test_build_snapshot_collects_profile_posts_and_trends(shared_source):
    before = datetime.now(UTC)
    snapshot = await build_snapshot(shared_source, "@Demo_Finanzas", 200)
    shared = load_snapshot()
    assert snapshot.profile == shared.profile
    assert snapshot.posts == shared.posts
    assert snapshot.trends == shared.trends
    assert snapshot.source == "twitterapi.io"
    assert before - timedelta(seconds=1) <= snapshot.collected_at <= datetime.now(UTC) + timedelta(seconds=1)

async def test_build_snapshot_respects_max_posts(shared_source):
    snapshot = await build_snapshot(shared_source, DEMO_HANDLE, 10)
    assert len(snapshot.posts) == 10

async def test_write_fixture_writes_snapshot_and_report(shared_source, out):
    snapshot = await build_snapshot(shared_source, DEMO_HANDLE, 200)
    paths = await write_fixture(snapshot, FakeAnalyzer(), out)
    assert paths == [out / f"{DEMO_HANDLE}.json", out / f"{DEMO_HANDLE}.report.json"]
    assert AccountSnapshot.model_validate_json(paths[0].read_text(encoding="utf-8")) == snapshot
    report = AnalysisReport.model_validate_json(paths[1].read_text(encoding="utf-8"))
    assert_report_matches_snapshot(report, snapshot)

async def test_written_files_are_pretty_json(shared_source, out):
    snapshot = await build_snapshot(shared_source, DEMO_HANDLE, 10)
    for path in await write_fixture(snapshot, FakeAnalyzer(), out):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("{\n  \"")
        json.loads(text)

async def test_write_fixture_overwrites(shared_source, out):
    out.mkdir()
    (out / f"{DEMO_HANDLE}.json").write_text("old", encoding="utf-8")
    snapshot = await build_snapshot(shared_source, DEMO_HANDLE, 10)
    await write_fixture(snapshot, FakeAnalyzer(), out)
    assert AccountSnapshot.model_validate_json((out / f"{DEMO_HANDLE}.json").read_text(encoding="utf-8")) == snapshot

async def test_written_files_are_served_by_demo_mode(shared_source, out):
    snapshot = await build_snapshot(shared_source, DEMO_HANDLE, 10)
    await write_fixture(snapshot, FakeAnalyzer(), out)
    served = await check_post_source(FixturePostSource(out), DEMO_HANDLE)
    assert served.profile == snapshot.profile
    assert [r.profile.handle for r in read_demo_reports(out)] == [DEMO_HANDLE]

def test_write_shared_writes_the_shared_fixture(out):
    paths = write_shared(out)
    assert paths == [out / f"{DEMO_HANDLE}.json", out / f"{DEMO_HANDLE}.report.json"]
    assert AccountSnapshot.model_validate_json(paths[0].read_text(encoding="utf-8")) == load_snapshot()
    assert AnalysisReport.model_validate_json(paths[1].read_text(encoding="utf-8")) == load_report()

async def test_run_writes_files_and_prints_one_line_per_file(settings, shared_source, out, capsys):
    code = await run([DEMO_HANDLE, "--out", str(out)], settings, source=shared_source, analyzer=FakeAnalyzer())
    assert code == 0
    assert sorted(p.name for p in out.iterdir()) == [f"{DEMO_HANDLE}.json", f"{DEMO_HANDLE}.report.json"]
    assert len([line for line in capsys.readouterr().out.splitlines() if line.strip()]) == 2

async def test_run_uses_max_posts(settings, shared_source, out):
    await run([DEMO_HANDLE, "--out", str(out), "--max-posts", "10"], settings, source=shared_source)
    snapshot = AccountSnapshot.model_validate_json((out / f"{DEMO_HANDLE}.json").read_text(encoding="utf-8"))
    assert len(snapshot.posts) == 10

async def test_run_defaults_to_the_fixtures_dir_and_the_settings_analyzer(settings, shared_source):
    code = await run([DEMO_HANDLE], settings, source=shared_source)
    assert code == 0
    report = AnalysisReport.model_validate_json(
        (settings.fixtures_dir / f"{DEMO_HANDLE}.report.json").read_text(encoding="utf-8")
    )
    assert report.engine == "fake"

async def test_run_with_include_shared(settings, out):
    api = FakeApi()
    source = TwitterApiIoSource("k", client=httpx.AsyncClient(transport=httpx.MockTransport(api)), backoff_base=0)
    code = await run(["mercadolibre", "--out", str(out), "--include-shared"], settings, source=source)
    assert code == 0
    assert sorted(p.name for p in out.iterdir()) == [
        f"{DEMO_HANDLE}.json", f"{DEMO_HANDLE}.report.json", "mercadolibre.json", "mercadolibre.report.json"
    ]
    served = FixturePostSource(out)
    assert (await served.fetch_profile("mercadolibre")).handle == "mercadolibre"
    assert (await served.fetch_profile(DEMO_HANDLE)).handle == DEMO_HANDLE

async def test_run_handles_several_accounts(settings, tmp_path, out):
    source_dir = tmp_path / "src"
    write_snapshot(source_dir, snapshot_for("alice"))
    write_snapshot(source_dir, snapshot_for("bob"))
    code = await run(["alice", "@Bob", "--out", str(out)], settings, source=FixturePostSource(source_dir))
    assert code == 0
    assert sorted(p.name for p in out.iterdir()) == ["alice.json", "alice.report.json", "bob.json", "bob.report.json"]

async def test_run_contract_error_exits_1_with_the_message(settings, shared_source, out, capsys):
    code = await run(["nobody", "--out", str(out)], settings, source=shared_source)
    assert code == 1
    captured = capsys.readouterr()
    assert "nobody" in captured.out + captured.err
    assert not out.exists() or not any(out.iterdir())

@pytest.mark.parametrize(
    "argv",
    [[], [DEMO_HANDLE, "--max-posts", "5"], [DEMO_HANDLE, "--max-posts", "501"], [DEMO_HANDLE, "--unknown"]],
)
async def test_run_bad_arguments_exit_2(settings, shared_source, argv):
    assert await run(argv, settings, source=shared_source) == 2

@pytest.mark.parametrize("key", [None, "", "  "])
async def test_run_without_a_key_exits_2(settings, out, key, capsys):
    no_key = settings.model_copy(update={"twitterapi_io_key": key})
    assert await run([DEMO_HANDLE, "--out", str(out)], no_key) == 2
    captured = capsys.readouterr()
    assert "TWITTERAPI_IO_KEY" in captured.out + captured.err
