import base64
import json

from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def _token(sub: str, role: str, territory_code: str = "WEST-01") -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload = (
        base64.urlsafe_b64encode(
            json.dumps({"sub": sub, "territory_code": territory_code, "role": role}).encode()
        )
        .decode()
        .rstrip("=")
    )
    return f"{header}.{payload}."


def authorized_client(token: str = REP_001) -> TestClient:
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
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
        assert "event: supervisor_decision" in body
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


def test_agent_run_creates_order_draft_and_requires_hitl(monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_run_enabled", True)
    with authorized_client() as c:
        response = c.post(
            "/api/v1/agent/run",
            json={
                "intent": "order_draft",
                "run_id": "run-order-draft",
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "session_id": "agent-run-order-draft",
                "items": [
                    {
                        "sku_id": "SKU-4001",
                        "sku_name": "Core SKU 4001",
                        "quantity": 4,
                        "reason": "Agent drafted replenishment only.",
                    }
                ],
                "notes": "Draft only; manager approval required.",
            },
        )
        assert response.status_code == 200
        body = response.text
        assert "event: supervisor_decision" in body
        assert "event: action_result" in body
        assert "event: hitl_required" in body
        assert "order_submit_requires_human_approval" in body
        assert "SUBMITTED_SANDBOX" not in body

        audit = c.get("/api/v1/audit/session/agent-run-order-draft")
        assert audit.status_code == 200
        assert any(event["event_type"] == "order_draft_created" for event in audit.json()["events"])


def test_agent_run_creates_visit_log_draft(monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_run_enabled", True)
    with authorized_client() as c:
        response = c.post(
            "/api/v1/agent/run",
            json={
                "intent": "visit_log_draft",
                "run_id": "run-visit-log",
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "session_id": "agent-run-visit-log",
                "outcome": "needs_follow_up",
                "notes": "Shelf check completed; follow-up needed.",
            },
        )
        assert response.status_code == 200
        body = response.text
        assert "event: action_result" in body
        assert "visit_log_draft" in body
        assert "event: hitl_required" not in body

        audit = c.get("/api/v1/audit/session/agent-run-visit-log")
        assert audit.status_code == 200
        assert any(event["event_type"] == "crm_visit_log_draft_created" for event in audit.json()["events"])


def test_agent_run_creates_manager_task_for_manager(monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_run_enabled", True)
    with authorized_client(_token("MGR-001", "manager")) as c:
        response = c.post(
            "/api/v1/agent/run",
            json={
                "intent": "manager_task",
                "run_id": "run-manager-task",
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "assigned_rep_id": "REP-001",
                "session_id": "agent-run-manager-task",
                "title": "Verify priority OOS alerts",
                "task_type": "shelf_check",
                "priority": "high",
                "alert_ids": ["ST-001:SKU-4001:2026-06-16"],
                "notes": "Created through supervisor action agent.",
            },
        )
        assert response.status_code == 200
        body = response.text
        assert "event: supervisor_decision" in body
        assert "action_agent" in body
        assert "manager_task" in body

        audit = c.get("/api/v1/audit/session/agent-run-manager-task")
        assert audit.status_code == 200
        assert any(event["event_type"] == "manager_task_created" for event in audit.json()["events"])


def test_agent_run_rejects_manager_task_for_rep(monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_run_enabled", True)
    with authorized_client() as c:
        response = c.post(
            "/api/v1/agent/run",
            json={
                "intent": "manager_task",
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "assigned_rep_id": "REP-001",
                "session_id": "agent-run-manager-denied",
                "title": "Verify priority OOS alerts",
                "task_type": "shelf_check",
                "priority": "high",
            },
        )
    assert response.status_code == 403
