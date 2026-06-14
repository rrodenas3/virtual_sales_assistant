from uuid import uuid4

from fastapi.testclient import TestClient

from backend.main import app


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def authorized_client() -> TestClient:
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {REP_001}"})
    return c


def test_today_store_alert_feedback_audit_smoke_path() -> None:
    session_id = f"smoke-{uuid4()}"
    with authorized_client() as c:
        visits = c.get("/api/v1/visits/today?territory_code=WEST-01&date=2026-06-14")
        assert visits.status_code == 200
        top_store_id = visits.json()[0]["store_id"]

        store = c.get(f"/api/v1/stores/{top_store_id}")
        assert store.status_code == 200
        assert store.json()["store_id"] == top_store_id

        alerts = c.get(f"/api/v1/stores/{top_store_id}/alerts?limit=1")
        assert alerts.status_code == 200
        alert = alerts.json()["alerts"][0]

        feedback = c.post(
            f"/api/v1/alerts/{alert['alert_id']}/feedback",
            json={"feedback": "confirmed", "session_id": session_id, "notes": "smoke path"},
        )
        assert feedback.status_code == 200
        feedback_body = feedback.json()
        assert feedback_body["alert_id"] == alert["alert_id"]
        assert feedback_body["audit_event_id"]

        audit = c.get(f"/api/v1/audit/session/{session_id}")
        assert audit.status_code == 200
        audit_body = audit.json()
        assert len(audit_body["feedback"]) == 1
        assert audit_body["feedback"][0]["alert_id"] == alert["alert_id"]
        assert any(event["event_type"] == "alert_feedback_created" for event in audit_body["events"])
