from conftest import DEMO_HANDLE, assert_error, report_for, snapshot_for, write_report, write_snapshot
from eduhub_shared.fixtures import load_report
from eduhub_shared.models import AnalysisReport

async def test_empty_fixtures_dir_seeds_the_shared_report(client):
    response = await client.get(f"/accounts/{DEMO_HANDLE}/report")
    assert response.status_code == 200
    assert AnalysisReport.model_validate(response.json()) == load_report()

async def test_report_files_in_fixtures_dir_are_seeded(make_client, fixtures_dir):
    write_snapshot(fixtures_dir, snapshot_for("alice"))
    write_report(fixtures_dir, report_for("alice", "r-alice"))
    write_report(fixtures_dir, report_for("bob", "r-bob"))
    async with make_client() as (client, _):
        alice = AnalysisReport.model_validate((await client.get("/accounts/alice/report")).json())
        bob = AnalysisReport.model_validate((await client.get("/accounts/bob/report")).json())
        assert alice.id == "r-alice"
        assert bob.id == "r-bob"
        assert (await client.get("/reports/r-alice")).status_code == 200

async def test_no_shared_fallback_when_fixtures_dir_has_files(make_client, fixtures_dir):
    write_snapshot(fixtures_dir, snapshot_for("alice"))
    write_report(fixtures_dir, report_for("alice", "r-alice"))
    async with make_client() as (client, _):
        assert_error(await client.get(f"/accounts/{DEMO_HANDLE}/report"), 404, "not_found")

async def test_nothing_is_seeded_when_demo_mode_is_off(make_client, settings, fixtures_dir):
    write_report(fixtures_dir, report_for("alice", "r-alice"))
    async with make_client(settings.model_copy(update={"demo_mode": False})) as (client, _):
        assert_error(await client.get("/accounts/alice/report"), 404, "not_found")
        assert_error(await client.get(f"/accounts/{DEMO_HANDLE}/report"), 404, "not_found")

async def test_seeding_twice_on_the_same_database_does_not_fail(make_client):
    async with make_client() as (client, _):
        assert (await client.get(f"/accounts/{DEMO_HANDLE}/report")).status_code == 200
    async with make_client() as (client, _):
        assert (await client.get(f"/accounts/{DEMO_HANDLE}/report")).status_code == 200
