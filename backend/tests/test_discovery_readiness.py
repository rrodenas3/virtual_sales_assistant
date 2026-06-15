from fastapi.testclient import TestClient
import pytest

from backend.adapters.factory import get_osa_data_port
from backend.config import settings
from backend.governance.discovery import readiness_blockers
from backend.main import app


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."
MANAGER = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJNR1ItMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6Im1hbmFnZXIifQ."


def test_readiness_endpoint_requires_manager_or_admin() -> None:
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/integrations/readiness")
    assert response.status_code == 403


def test_readiness_reports_default_local_mode() -> None:
    with TestClient(app, headers={"Authorization": f"Bearer {MANAGER}"}) as client:
        response = client.get("/api/v1/integrations/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["selected_live_modes"] == []
    assert body["view_contract_validated"] is False
    assert body["last_validation_at"] is None
    assert body["validation_summary"] is None
    assert any(gate["setting_name"] == "discovery_sso_provider" for gate in body["gates"])


def test_readiness_reports_live_contract_validation_status(monkeypatch) -> None:
    monkeypatch.setattr(settings, "live_data_contract_validated", True)
    monkeypatch.setattr(settings, "live_data_contract_last_validation_at", "2026-06-15T08:00:00Z")
    monkeypatch.setattr(settings, "live_data_contract_validation_summary", "3 contracts valid")
    with TestClient(app, headers={"Authorization": f"Bearer {MANAGER}"}) as client:
        response = client.get("/api/v1/integrations/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["view_contract_validated"] is True
    assert body["last_validation_at"] == "2026-06-15T08:00:00Z"
    assert body["validation_summary"] == "3 contracts valid"


def test_live_databricks_mode_is_blocked_by_missing_discovery(monkeypatch) -> None:
    monkeypatch.setattr(settings, "osa_adapter", "databricks")
    monkeypatch.setattr(settings, "discovery_data_sharing_model", None)
    monkeypatch.setattr(settings, "discovery_data_residency", None)
    get_osa_data_port.cache_clear()
    blockers = readiness_blockers()
    assert "discovery_data_sharing_model" in blockers
    assert "discovery_data_residency" in blockers
    with pytest.raises(RuntimeError, match="discovery_data_sharing_model"):
        get_osa_data_port()
    get_osa_data_port.cache_clear()


def test_external_shelf_image_mode_requires_data_residency(monkeypatch) -> None:
    monkeypatch.setattr(settings, "shelf_image_adapter", "external")
    monkeypatch.setattr(settings, "discovery_data_residency", None)
    blockers = readiness_blockers()
    assert "discovery_data_residency" in blockers


def test_external_jwt_discovery_gate_precedes_provider_config_check(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_provider", "external_jwt")
    monkeypatch.setattr(settings, "discovery_sso_provider", None)
    monkeypatch.setattr(settings, "external_jwt_issuer", None)
    monkeypatch.setattr(settings, "external_jwt_audience", None)
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/visits/today?territory_code=WEST-01")
    assert response.status_code == 503
    assert "discovery_sso_provider" in response.json()["message"]
