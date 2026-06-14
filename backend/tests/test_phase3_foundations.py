from uuid import uuid4

from fastapi.testclient import TestClient

from backend.main import app


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def authorized_client() -> TestClient:
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {REP_001}"})
    return c


def _create_draft(c: TestClient, session_id: str = "phase3-submit") -> dict:
    return c.post(
        "/api/v1/orders/drafts",
        json={
            "store_id": "ST-001",
            "session_id": session_id,
            "items": [
                {
                    "sku_id": "SKU-4001",
                    "sku_name": "Core SKU 4001",
                    "quantity": 10,
                    "reason": "Sandbox submit test",
                }
            ],
        },
    ).json()


def test_sandbox_submit_requires_matching_approval() -> None:
    with authorized_client() as c:
        draft = _create_draft(c)
        rejected = c.post(f"/api/v1/orders/drafts/{draft['draft_id']}/submit-sandbox")
        assert rejected.status_code == 409

        approval = c.post(f"/api/v1/approvals/{draft['draft_id']}/approve", json={"notes": "ok"})
        assert approval.status_code == 200

        submitted = c.post(f"/api/v1/orders/drafts/{draft['draft_id']}/submit-sandbox")
        assert submitted.status_code == 200
        body = submitted.json()
        assert body["status"] == "SUBMITTED_SANDBOX"
        assert body["erp_order_id"].startswith("SANDBOX-")
        assert body["payload_hash"] == draft["payload_hash"]


def test_offline_feedback_sync_is_idempotent() -> None:
    with authorized_client() as c:
        alert = c.get("/api/v1/stores/ST-001/alerts").json()["alerts"][0]
        idempotency_key = f"REP-001:{uuid4()}"
        payload = {
            "events": [
                {
                    "idempotency_key": idempotency_key,
                    "alert_id": alert["alert_id"],
                    "feedback": "needs_follow_up",
                    "session_id": "offline-sync-test",
                    "notes": "queued offline",
                }
            ]
        }

        first = c.post("/api/v1/sync/feedback-events", json=payload)
        assert first.status_code == 200
        first_body = first.json()
        assert first_body["results"][0]["status"] == "created"

        second = c.post("/api/v1/sync/feedback-events", json=payload)
        assert second.status_code == 200
        second_body = second.json()
        assert second_body["results"][0]["status"] == "duplicate"
        assert second_body["results"][0]["feedback"]["id"] == first_body["results"][0]["feedback"]["id"]


def test_summary_audit_contains_cost_telemetry() -> None:
    with authorized_client() as c:
        alerts = c.get("/api/v1/stores/ST-001/alerts").json()["alerts"][:2]
        response = c.post(
            "/api/v1/agent/osa-summary",
            json={
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "session_id": "cost-telemetry-test",
                "alert_ids": [alert["alert_id"] for alert in alerts],
            },
        )
        assert response.status_code == 200
        audit = c.get("/api/v1/audit/session/cost-telemetry-test").json()
        summary_events = [event for event in audit["events"] if event["event_type"] == "osa_summary_created"]
        assert summary_events
        payload = summary_events[0]["payload_json"]
        assert payload["estimated_input_tokens"] > 0
        assert payload["estimated_output_tokens"] > 0
        assert payload["estimated_cost_eur"] > 0
