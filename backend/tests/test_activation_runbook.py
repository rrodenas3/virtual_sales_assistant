from fastapi.testclient import TestClient

from backend.config import settings
from backend.governance.activation import build_activation_targets, runtime_validation_command_sets
from backend.governance.activation_runbook import build_activation_runbook
from backend.main import app

REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."
MANAGER = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJNR1ItMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6Im1hbmFnZXIifQ."


def test_activation_runbook_endpoint_requires_manager_or_admin() -> None:
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/integrations/activation-runbook?target=pilot")
    assert response.status_code == 403


def test_activation_runbook_endpoint_returns_phase_plan() -> None:
    with TestClient(app, headers={"Authorization": f"Bearer {MANAGER}"}) as client:
        response = client.get("/api/v1/integrations/activation-runbook?target=pilot")
    assert response.status_code == 200
    body = response.json()
    assert body["current_target"] == "pilot"
    assert body["phase_count"] == 8
    assert body["blocked_phase_count"] >= 3
    assert "governed VSA pilot" in body["final_outcome"]
    phases = {phase["phase_id"]: phase for phase in body["phases"]}
    assert phases["phase-0-local-scaffold"]["status"] == "ready"
    assert phases["phase-1-ai-demo"]["status"] == "blocked"
    assert phases["phase-2-live-data-contracts"]["status"] == "blocked"
    assert phases["phase-6-final-pilot"]["target"] == "pilot"
    assert "ai_summary_eval" in phases["phase-1-ai-demo"]["required_command_names"]
    assert "SUMMARY_PROVIDER" in phases["phase-1-ai-demo"]["required_configuration_keys"]
    assert "pilot_readiness" in phases["phase-6-final-pilot"]["required_command_names"]
    assert body["public_safety_notes"]


def test_activation_runbook_builder_marks_ai_demo_ready_when_target_clear(monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_run_enabled", True)
    activation_targets = build_activation_targets(
        discovery_blockers=[],
        provider_blockers=[],
        provider_readiness={"audit": {"unity_selected": False}},
        summary_status={
            "ai_demo_blockers": [],
        },
    )
    report = build_activation_runbook(
        current_target="ai-demo",
        activation_targets=[dict(item) for item in activation_targets],
        provider_readiness={
            "data_platform": {"ready": True, "blockers": []},
            "auth": {"ready": True, "blockers": []},
            "audit": {"ready": True, "blockers": []},
            "guardrails": {"ready": True, "blockers": []},
            "action_providers": {"ready": True, "blockers": []},
            "memory": {"ready": True, "blockers": []},
            "offline_agent": {"ready": True, "blockers": []},
            "shelf_image": {"ready": True, "blockers": []},
        },
        runtime_validation_commands=runtime_validation_command_sets(),
    )
    phases = {phase["phase_id"]: phase for phase in report["phases"]}
    assert phases["phase-1-ai-demo"]["status"] == "ready"
    assert phases["phase-1-ai-demo"]["blockers"] == []
