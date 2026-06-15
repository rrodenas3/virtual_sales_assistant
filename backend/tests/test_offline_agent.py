from fastapi.testclient import TestClient

from backend.config import settings
from backend.governance.discovery import readiness_blockers, selected_live_modes
from backend.governance.offline_agent import offline_agent_status
from backend.main import app

REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def test_offline_agent_health_defaults_to_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "offline_agent_enabled", False)
    monkeypatch.setattr(settings, "offline_agent_provider", "none")
    monkeypatch.setattr(settings, "offline_agent_kill_switch", True)

    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/health/offline-agent")

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is False
    assert body["provider"] == "none"
    assert "OFFLINE_AGENT_ENABLED must be true after spike approval" in body["blockers"]


def test_offline_agent_status_requires_kill_switch_and_thresholds(monkeypatch) -> None:
    monkeypatch.setattr(settings, "offline_agent_enabled", True)
    monkeypatch.setattr(settings, "offline_agent_provider", "hermes")
    monkeypatch.setattr(settings, "offline_agent_kill_switch", False)
    monkeypatch.setattr(settings, "offline_agent_min_device_ram_gb", 8.0)
    monkeypatch.setattr(settings, "offline_agent_max_latency_ms", 2500)
    monkeypatch.setattr(settings, "offline_agent_min_tool_accuracy", 0.95)

    status = offline_agent_status()

    assert status["ready"] is True
    assert status["blockers"] == []


def test_offline_agent_selected_mode_is_discovery_gated(monkeypatch) -> None:
    monkeypatch.setattr(settings, "offline_agent_enabled", True)
    monkeypatch.setattr(settings, "offline_agent_provider", "ollama")
    monkeypatch.setattr(settings, "discovery_rep_device", None)
    monkeypatch.setattr(settings, "discovery_offline_sync_policy", None)

    assert "offline_agent" in selected_live_modes()
    blockers = readiness_blockers()
    assert "discovery_rep_device" in blockers
    assert "discovery_offline_sync_policy" in blockers
