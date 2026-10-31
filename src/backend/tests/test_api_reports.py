from conftest import DEMO_HANDLE, assert_error
from eduhub_shared.fixtures import load_report
from eduhub_shared.models import AnalysisReport

async def test_unknown_report_is_404(client):
    assert_error(await client.get("/reports/missing"), 404, "not_found")

async def test_latest_report_of_a_seeded_account(client):
    response = await client.get(f"/accounts/{DEMO_HANDLE}/report")
    assert response.status_code == 200
    assert AnalysisReport.model_validate(response.json()) == load_report()

async def test_latest_report_handle_is_normalized(client):
    response = await client.get("/accounts/@Demo_Finanzas/report")
    assert response.status_code == 200
    assert response.json()["profile"]["handle"] == DEMO_HANDLE

async def test_account_without_reports_is_404(client):
    assert_error(await client.get("/accounts/nobody/report"), 404, "not_found")

async def test_invalid_handle_in_path_is_404(client):
    assert_error(await client.get("/accounts/not-a-handle!/report"), 404, "not_found")

async def test_report_by_id(client):
    report = load_report()
    response = await client.get(f"/reports/{report.id}")
    assert response.status_code == 200
    assert AnalysisReport.model_validate(response.json()) == report
