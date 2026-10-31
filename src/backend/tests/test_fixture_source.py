import pytest
from conftest import DEMO_HANDLE, report_for, snapshot_for, write_report, write_snapshot
from eduhub_backend.sources.fixture import FixturePostSource
from eduhub_shared.errors import AccountNotFoundError
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.testing import check_post_source

async def test_empty_directory_falls_back_to_shared_fixture(fixtures_dir):
    source = FixturePostSource(fixtures_dir)
    snapshot = await check_post_source(source, DEMO_HANDLE)
    assert snapshot.profile == load_snapshot().profile

async def test_missing_directory_falls_back_to_shared_fixture(tmp_path):
    source = FixturePostSource(tmp_path / "does_not_exist")
    await check_post_source(source, DEMO_HANDLE)

async def test_fallback_serves_shared_posts_and_trends(fixtures_dir):
    source = FixturePostSource(fixtures_dir)
    shared = load_snapshot()
    assert await source.fetch_posts(DEMO_HANDLE, 500) == shared.posts
    assert await source.fetch_trends() == shared.trends

async def test_serves_one_snapshot_per_handle_file(fixtures_dir):
    write_snapshot(fixtures_dir, snapshot_for("alice"))
    write_snapshot(fixtures_dir, snapshot_for("bob"))
    source = FixturePostSource(fixtures_dir)
    alice = await check_post_source(source, "alice")
    bob = await check_post_source(source, "bob")
    assert alice.profile.handle == "alice"
    assert bob.profile.handle == "bob"

async def test_no_fallback_when_directory_has_snapshots(fixtures_dir):
    write_snapshot(fixtures_dir, snapshot_for("alice"))
    source = FixturePostSource(fixtures_dir)
    with pytest.raises(AccountNotFoundError):
        await source.fetch_profile(DEMO_HANDLE)

async def test_unknown_handle_raises_account_not_found(fixtures_dir):
    source = FixturePostSource(fixtures_dir)
    with pytest.raises(AccountNotFoundError):
        await source.fetch_profile("nobody")
    with pytest.raises(AccountNotFoundError):
        await source.fetch_posts("nobody", 10)

async def test_handle_is_normalized(fixtures_dir):
    source = FixturePostSource(fixtures_dir)
    profile = await source.fetch_profile("@Demo_Finanzas")
    assert profile.handle == DEMO_HANDLE

async def test_limit_is_respected(fixtures_dir):
    source = FixturePostSource(fixtures_dir)
    posts = await source.fetch_posts(DEMO_HANDLE, 10)
    assert posts == load_snapshot().posts[:10]

async def test_report_files_are_not_snapshots(fixtures_dir):
    write_snapshot(fixtures_dir, snapshot_for("alice"))
    write_report(fixtures_dir, report_for("alice", "r-alice"))
    source = FixturePostSource(fixtures_dir)
    await check_post_source(source, "alice")
    with pytest.raises(AccountNotFoundError):
        await source.fetch_profile("alice.report")
