from fastapi.testclient import TestClient

from backend.config import settings
from backend.governance.action_providers import action_provider_status
from backend.main import app


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def test_action_provider_status_reports_default_ready(monkeypatch) -> None:
    monkeypatch.setattr(settings, "crm_adapter", "local")
    monkeypatch.setattr(settings, "erp_adapter", "sandbox")
    monkeypatch.setattr(settings, "crm_endpoint", None)
    monkeypatch.setattr(settings, "crm_token_ref", None)
    monkeypatch.setattr(settings, "erp_endpoint", None)
    monkeypatch.setattr(settings, "erp_token_ref", None)

    status = action_provider_status()

    assert status["ready"] is True
    assert status["crm"]["provider"] == "local"
    assert status["erp"]["provider"] == "sandbox"
    assert status["blockers"] == []


def test_action_provider_status_reports_external_blockers(monkeypatch) -> None:
    monkeypatch.setattr(settings, "crm_adapter", "external")
    monkeypatch.setattr(settings, "erp_adapter", "external")
    monkeypatch.setattr(settings, "crm_endpoint", None)
    monkeypatch.setattr(settings, "crm_token_ref", None)
    monkeypatch.setattr(settings, "erp_endpoint", None)
    monkeypatch.setattr(settings, "erp_token_ref", None)
    monkeypatch.setattr(settings, "discovery_crm_platform", None)
    monkeypatch.setattr(settings, "discovery_erp_sandbox", None)

    status = action_provider_status()

    assert status["ready"] is False
    assert status["blockers"] == [
        "crm.crm_endpoint",
        "crm.crm_token_ref",
        "crm.discovery_crm_platform",
        "erp.erp_endpoint",
        "erp.erp_token_ref",
        "erp.discovery_erp_sandbox",
    ]


def test_action_provider_status_reports_external_ready(monkeypatch) -> None:
    monkeypatch.setattr(settings, "crm_adapter", "external")
    monkeypatch.setattr(settings, "erp_adapter", "external")
    monkeypatch.setattr(settings, "crm_endpoint", "https://crm.example.test")
    monkeypatch.setattr(settings, "crm_token_ref", "approved-token-reference")
    monkeypatch.setattr(settings, "erp_endpoint", "https://erp.example.test")
    monkeypatch.setattr(settings, "erp_token_ref", "approved-token-reference")
    monkeypatch.setattr(settings, "discovery_crm_platform", "approved-crm")
    monkeypatch.setattr(settings, "discovery_erp_sandbox", "approved-sandbox")

    status = action_provider_status()

    assert status["ready"] is True
    assert status["crm"]["endpoint_configured"] is True
    assert status["erp"]["token_ref_configured"] is True
    assert status["blockers"] == []


def test_action_provider_health_endpoint_reports_selected_modes(monkeypatch) -> None:
    monkeypatch.setattr(settings, "crm_adapter", "external")
    monkeypatch.setattr(settings, "erp_adapter", "sandbox")
    monkeypatch.setattr(settings, "crm_endpoint", "https://crm.example.test")
    monkeypatch.setattr(settings, "crm_token_ref", None)
    monkeypatch.setattr(settings, "discovery_crm_platform", "approved-crm")

    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/health/action-providers")

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is False
    assert body["crm"]["provider"] == "external"
    assert body["erp"]["provider"] == "sandbox"
    assert body["blockers"] == ["crm.crm_token_ref"]
