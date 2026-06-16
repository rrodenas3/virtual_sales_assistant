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
    assert body["summary_provider"] == "template"
    assert body["summary_model_id"] == "grounded-template-v1"
    assert body["ai_demo_ready"] is False
    assert body["ai_demo_provider_ready"] is False
    assert body["ai_demo_eval_validated"] is False
    assert body["ai_demo_eval_last_validation_at"] is None
    assert body["ai_demo_eval_validation_summary"] is None
    assert body["ai_demo_stage"] == "template_scaffold"
    assert body["ai_demo_next_actions"][0] == "Set SUMMARY_PROVIDER=anthropic in the approved AI-demo runtime"
    assert body["ai_demo_validation_command"] == "python scripts/run_eval.py --require-provider anthropic --output-dir artifacts/eval-ai"
    assert body["provider_blockers"] == []
    assert body["provider_readiness"]["auth"]["provider"] == "mock"
    assert body["provider_readiness"]["data_platform"]["ready"] is True
    assert body["provider_readiness"]["audit"]["primary_sink"] == "postgres"
    assert body["provider_readiness"]["observability"]["provider"] == "structured"
    assert "SUMMARY_PROVIDER must be anthropic for AI-demo readiness" in body["ai_demo_blockers"]
    assert "AI-demo eval must pass with provider=anthropic before AI-demo readiness" in body["ai_demo_blockers"]
    assert any(gate["setting_name"] == "discovery_sso_provider" for gate in body["gates"])
    assert {gate["owner"] for gate in body["gates"]} >= {"delivery", "shared"}
    targets = {target["target"]: target for target in body["activation_targets"]}
    assert targets["local"]["ready"] is True
    assert targets["local"]["blockers"] == []
    assert targets["ai-demo"]["ready"] is False
    assert "AGENT_RUN_ENABLED must be true for AI-demo readiness" in targets["ai-demo"]["blockers"]
    assert targets["pilot"]["ready"] is False
    assert "Live data contracts must be validated for pilot readiness" in targets["pilot"]["blockers"]
    assert body["runtime_validation_commands"]["local"][0]["name"] == "public_safety_scan"
    assert body["runtime_validation_commands"]["local"][1]["name"] == "spec_decision_guard"
    assert any(command["name"] == "local_dev_smoke" for command in body["runtime_validation_commands"]["local"])
    assert body["runtime_validation_commands"]["local"][-1]["name"] == "validation_suite"
    assert any(command["name"] == "summary_load_test" for command in body["runtime_validation_commands"]["ai-demo"])
    assert any(command["name"] == "ai_summary_eval" for command in body["runtime_validation_commands"]["ai-demo"])
    assert any(command["name"] == "mlflow_handoff_dry_run" for command in body["runtime_validation_commands"]["ai-demo"])
    assert any(command["name"] == "ai_demo_eval_evidence" for command in body["runtime_validation_commands"]["ai-demo"])
    assert any(command["name"] == "pilot_readiness" for command in body["runtime_validation_commands"]["pilot"])
    assert body["runtime_validation_commands"]["pilot"][-1]["name"] == "validation_suite"


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


def test_readiness_reports_ai_demo_provider_state(monkeypatch) -> None:
    monkeypatch.setattr(settings, "summary_provider", "anthropic")
    monkeypatch.setattr(settings, "anthropic_token_ref", "token-ref")
    monkeypatch.setattr(settings, "anthropic_model", "claude-haiku-4-5")
    monkeypatch.setattr(settings, "ai_demo_eval_validated", True)
    monkeypatch.setattr(settings, "ai_demo_eval_last_validation_at", "2026-06-15T10:00:00Z")
    monkeypatch.setattr(settings, "ai_demo_eval_validation_summary", "provider=anthropic passed")
    with TestClient(app, headers={"Authorization": f"Bearer {MANAGER}"}) as client:
        response = client.get("/api/v1/integrations/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["summary_provider"] == "anthropic"
    assert body["summary_model_id"] == "claude-haiku-4-5"
    assert body["ai_demo_ready"] is True
    assert body["ai_demo_provider_ready"] is True
    assert body["ai_demo_eval_validated"] is True
    assert body["ai_demo_eval_last_validation_at"] == "2026-06-15T10:00:00Z"
    assert body["ai_demo_eval_validation_summary"] == "provider=anthropic passed"
    assert body["ai_demo_stage"] == "validated"
    assert body["ai_demo_next_actions"] == ["No AI-demo action required"]
    assert body["ai_demo_blockers"] == []
    targets = {target["target"]: target for target in body["activation_targets"]}
    assert targets["ai-demo"]["ready"] is False
    assert targets["ai-demo"]["blockers"] == ["AGENT_RUN_ENABLED must be true for AI-demo readiness"]


def test_readiness_reports_provider_configuration_blockers(monkeypatch) -> None:
    monkeypatch.setattr(settings, "crm_adapter", "external")
    monkeypatch.setattr(settings, "crm_endpoint", "https://crm.example.test")
    monkeypatch.setattr(settings, "crm_token_ref", None)
    monkeypatch.setattr(settings, "discovery_crm_platform", "approved-crm")

    with TestClient(app, headers={"Authorization": f"Bearer {MANAGER}"}) as client:
        response = client.get("/api/v1/integrations/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is False
    assert body["blockers"] == []
    assert body["provider_readiness"]["action_providers"]["ready"] is False
    assert body["provider_blockers"] == ["action_providers.crm.crm_token_ref"]


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
