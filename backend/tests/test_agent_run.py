from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def authorized_client() -> TestClient:
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {REP_001}"})
    return c


def test_agent_run_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_run_enabled", False)
    with authorized_client() as c:
        response = c.post(
            "/api/v1/agent/run",
            json={"territory_code": "WEST-01", "session_id": "disabled-agent-run"},
        )
    assert response.status_code == 404


def test_agent_run_streams_grounded_summary_events(monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_run_enabled", True)
    with authorized_client() as c:
        alerts = c.get("/api/v1/stores/ST-001/alerts").json()["alerts"][:2]
        response = c.post(
            "/api/v1/agent/run",
            json={
                "run_id": "run-test-1",
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "session_id": "agent-run-test",
                "alert_ids": [alert["alert_id"] for alert in alerts],
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = response.text
        assert "event: run_started" in body
        assert "event: message" in body
        assert "event: audit" in body
        assert "event: run_completed" in body
        assert "run-test-1" in body
        assert alerts[0]["alert_id"] in body

        audit = c.get("/api/v1/audit/session/agent-run-test")
        assert audit.status_code == 200
        assert any(event["event_type"] == "osa_summary_created" for event in audit.json()["events"])


def test_agent_run_rejects_ungrounded_alert_ids(monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_run_enabled", True)
    with authorized_client() as c:
        response = c.post(
            "/api/v1/agent/run",
            json={
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "session_id": "agent-run-reject-test",
                "alert_ids": ["ST-999:SKU-9999:2026-06-15"],
            },
        )
    assert response.status_code == 400
