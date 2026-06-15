from fastapi.testclient import TestClient

from backend.config import settings
from backend.governance.data_platform import data_platform_status
from backend.main import app


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def test_data_platform_status_reports_mock_defaults_ready(monkeypatch) -> None:
    monkeypatch.setattr(settings, "osa_adapter", "mock")
    monkeypatch.setattr(settings, "rgm_adapter", "mock")
    monkeypatch.setattr(settings, "store_master_adapter", "mock")
    monkeypatch.setattr(settings, "live_data_contract_validated", False)

    status = data_platform_status()

    assert status["ready"] is True
    assert status["databricks"]["selected"] is False
    assert status["snowflake"]["selected"] is False
    assert status["blockers"] == []


def test_data_platform_status_reports_live_blockers(monkeypatch) -> None:
    monkeypatch.setattr(settings, "osa_adapter", "databricks")
    monkeypatch.setattr(settings, "rgm_adapter", "databricks")
    monkeypatch.setattr(settings, "store_master_adapter", "snowflake")
    monkeypatch.setattr(settings, "databricks_host", None)
    monkeypatch.setattr(settings, "databricks_token", None)
    monkeypatch.setattr(settings, "databricks_sql_warehouse_id", None)
    monkeypatch.setattr(settings, "snowflake_account", None)
    monkeypatch.setattr(settings, "snowflake_user", None)
    monkeypatch.setattr(settings, "snowflake_token", None)
    monkeypatch.setattr(settings, "snowflake_warehouse", None)
    monkeypatch.setattr(settings, "snowflake_database", None)
    monkeypatch.setattr(settings, "snowflake_schema", None)
    monkeypatch.setattr(settings, "discovery_data_sharing_model", None)
    monkeypatch.setattr(settings, "discovery_data_residency", None)
    monkeypatch.setattr(settings, "live_data_contract_validated", False)

    status = data_platform_status()

    assert status["ready"] is False
    assert "databricks.databricks_host" in status["blockers"]
    assert "databricks.live_data_contract_validated" in status["blockers"]
    assert "snowflake.snowflake_account" in status["blockers"]
    assert "snowflake.snowflake_token" in status["blockers"]
    assert "snowflake.live_data_contract_validated" in status["blockers"]


def test_data_platform_status_reports_live_ready(monkeypatch) -> None:
    monkeypatch.setattr(settings, "osa_adapter", "databricks")
    monkeypatch.setattr(settings, "rgm_adapter", "mock")
    monkeypatch.setattr(settings, "store_master_adapter", "snowflake")
    monkeypatch.setattr(settings, "databricks_host", "https://dbc.example.test")
    monkeypatch.setattr(settings, "databricks_token", "approved-token-reference")
    monkeypatch.setattr(settings, "databricks_sql_warehouse_id", "warehouse-1")
    monkeypatch.setattr(settings, "snowflake_account", "acct")
    monkeypatch.setattr(settings, "snowflake_user", "svc_user")
    monkeypatch.setattr(settings, "snowflake_token", "approved-token-reference")
    monkeypatch.setattr(settings, "snowflake_warehouse", "warehouse")
    monkeypatch.setattr(settings, "snowflake_database", "database")
    monkeypatch.setattr(settings, "snowflake_schema", "schema")
    monkeypatch.setattr(settings, "discovery_data_sharing_model", "approved-sharing")
    monkeypatch.setattr(settings, "discovery_data_residency", "approved-region")
    monkeypatch.setattr(settings, "live_data_contract_validated", True)

    status = data_platform_status()

    assert status["ready"] is True
    assert status["databricks"]["selected"] is True
    assert status["snowflake"]["selected"] is True
    assert status["blockers"] == []


def test_data_platform_health_endpoint_reports_selected_modes(monkeypatch) -> None:
    monkeypatch.setattr(settings, "osa_adapter", "databricks")
    monkeypatch.setattr(settings, "rgm_adapter", "mock")
    monkeypatch.setattr(settings, "store_master_adapter", "mock")
    monkeypatch.setattr(settings, "databricks_host", "https://dbc.example.test")
    monkeypatch.setattr(settings, "databricks_token", None)
    monkeypatch.setattr(settings, "databricks_sql_warehouse_id", "warehouse-1")
    monkeypatch.setattr(settings, "discovery_data_sharing_model", "approved-sharing")
    monkeypatch.setattr(settings, "discovery_data_residency", "approved-region")
    monkeypatch.setattr(settings, "live_data_contract_validated", True)

    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/health/data-platform")

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is False
    assert body["databricks"]["selected"] is True
    assert body["snowflake"]["selected"] is False
    assert body["blockers"] == ["databricks.databricks_token"]
