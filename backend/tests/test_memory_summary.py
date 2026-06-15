from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def test_summary_audit_records_null_memory_metadata(monkeypatch) -> None:
    monkeypatch.setattr(settings, "memory_provider", "none")
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        alerts = client.get("/api/v1/stores/ST-001/alerts").json()["alerts"][:1]
        response = client.post(
            "/api/v1/agent/osa-summary",
            json={
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "session_id": "memory-summary-test",
                "alert_ids": [alert["alert_id"] for alert in alerts],
            },
        )
        assert response.status_code == 200
        audit = client.get("/api/v1/audit/session/memory-summary-test").json()
    summary_events = [event for event in audit["events"] if event["event_type"] == "osa_summary_created"]
    assert summary_events
    payload = summary_events[-1]["payload_json"]
    assert payload["memory_provider"] == "none"
    assert payload["memory_count"] == 0
