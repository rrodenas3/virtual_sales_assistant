from fastapi.testclient import TestClient

from backend.main import app


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def authorized_client() -> TestClient:
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {REP_001}"})
    return c


def test_pilot_metrics_aggregate_feedback_audit_and_cost() -> None:
    with authorized_client() as c:
        alert = c.get("/api/v1/stores/ST-001/alerts").json()["alerts"][0]
        feedback_response = c.post(
            f"/api/v1/alerts/{alert['alert_id']}/feedback",
            json={"feedback": "confirmed", "session_id": "metrics-test"},
        )
        assert feedback_response.status_code == 200
        summary_response = c.post(
            "/api/v1/agent/osa-summary",
            json={
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "session_id": "metrics-test",
                "alert_ids": [alert["alert_id"]],
            },
        )
        assert summary_response.status_code == 200

        metrics = c.get("/api/v1/metrics/pilot")
        assert metrics.status_code == 200
        body = metrics.json()
        assert body["feedback_count"] >= 1
        assert body["confirmed_count"] >= 1
        assert body["summary_count"] >= 1
        assert body["avg_estimated_cost_eur"] > 0
        assert body["trace_event_counts"]["alert_feedback_created"] >= 1
        assert body["trace_event_counts"]["osa_summary_created"] >= 1

