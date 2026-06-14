from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app, should_auto_create_tables


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def test_auto_create_tables_is_disabled_for_production(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "auto_create_tables", True)
    assert should_auto_create_tables() is False


def test_auto_create_tables_respects_explicit_disable(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "local")
    monkeypatch.setattr(settings, "auto_create_tables", False)
    assert should_auto_create_tables() is False


def test_db_health_endpoint_reports_reachable_database() -> None:
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    assert response.json()["database"] == "reachable"
