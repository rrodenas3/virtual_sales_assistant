from fastapi.testclient import TestClient

from backend.main import app


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."
REP_002 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAyIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def authorized_client(token: str = REP_001) -> TestClient:
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


def test_today_visits_are_ranked_with_components() -> None:
    with authorized_client() as c:
        response = c.get("/api/v1/visits/today?territory_code=WEST-01&date=2026-06-14")
        assert response.status_code == 200
        rows = response.json()
    assert rows
    assert rows == sorted(rows, key=lambda row: (-row["priority_score"], -row["oos_sku_count"], row["store_id"]))
    assert {"oos_risk", "promo_gap", "revenue_opportunity", "visit_recency"} <= set(rows[0]["components"])
    assert rows[0]["audit_event_ids"]


def test_backend_root_points_to_api() -> None:
    with authorized_client() as c:
        response = c.get("/")
        assert response.status_code == 200
        assert response.json()["health"] == "/api/v1/health"

        api_index = c.get("/api/v1")
        assert api_index.status_code == 200
        assert "GET /api/v1/health" in api_index.json()["routes"]
        assert "POST /api/v1/sync/feedback-events" in api_index.json()["routes"]
        assert "POST /api/v1/orders/drafts/{draft_id}/submit-sandbox" in api_index.json()["routes"]
        assert "POST /api/v1/agent/run" in api_index.json()["routes"]
        assert "POST /api/v1/stores/{store_id}/shelf-image-analysis" in api_index.json()["routes"]
        assert "GET /api/v1/health/memory" in api_index.json()["routes"]
        assert "GET /api/v1/health/action-providers" in api_index.json()["routes"]
        assert "GET /api/v1/health/data-platform" in api_index.json()["routes"]


def test_unauthorized_store_access_returns_404() -> None:
    with authorized_client(REP_002) as c:
        response = c.get("/api/v1/stores/ST-001")
        assert response.status_code == 404
        assert response.json()["code"] == "http_error"


def test_alerts_include_deterministic_action_and_trace_fields() -> None:
    with authorized_client() as c:
        response = c.get("/api/v1/stores/ST-001/alerts?limit=50")
        assert response.status_code == 200
        alerts = response.json()["alerts"]
    assert alerts
    alert = alerts[0]
    assert alert["alert_id"].startswith("ST-001:")
    assert alert["recommended_action"]
    assert alert["confidence_label"] in {"low", "medium", "high"}
    assert alert["prediction_row_id"]
    assert alert["model_version"] == "mock-v1"
    assert alert["audit_event_id"]


def test_feedback_writes_feedback_and_audit() -> None:
    with authorized_client() as c:
        alert = c.get("/api/v1/stores/ST-001/alerts").json()["alerts"][0]
        response = c.post(
            f"/api/v1/alerts/{alert['alert_id']}/feedback",
            json={"feedback": "confirmed", "session_id": "test-session"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["feedback"] == "confirmed"
        assert body["audit_event_id"]
        audit = c.get("/api/v1/audit/session/test-session")
        assert audit.status_code == 200
        assert any(event["event_type"] == "alert_feedback_created" for event in audit.json()["events"])


def test_osa_summary_is_grounded_and_rejects_unknown_alerts() -> None:
    with authorized_client() as c:
        alerts = c.get("/api/v1/stores/ST-001/alerts").json()["alerts"]
        alert_ids = [alert["alert_id"] for alert in alerts[:2]]
        response = c.post(
            "/api/v1/agent/osa-summary",
            json={
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "session_id": "summary-test",
                "alert_ids": alert_ids,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert set(body["grounded_alert_ids"]) == set(alert_ids)
        allowed_skus = {alert["sku_name"] for alert in alerts[:2]}
        assert any(sku in body["summary"] for sku in allowed_skus)

        rejected = c.post(
            "/api/v1/agent/osa-summary",
            json={
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "session_id": "summary-test",
                "alert_ids": ["ST-999:SKU-9999:2026-06-14"],
            },
        )
        assert rejected.status_code == 400


def test_shelf_image_analysis_is_grounded_and_audited() -> None:
    with authorized_client() as c:
        alert = c.get("/api/v1/stores/ST-001/alerts").json()["alerts"][0]
        response = c.post(
            "/api/v1/stores/ST-001/shelf-image-analysis",
            json={
                "store_id": "ST-001",
                "session_id": "shelf-session",
                "image_ref": "upload://shelf-session/image-1",
                "alert_ids": [alert["alert_id"]],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["store_id"] == "ST-001"
        assert body["findings"][0]["grounded_alert_id"] == alert["alert_id"]
        assert body["source_system"] == "mock"
        assert body["audit_event_id"]

        audit = c.get("/api/v1/audit/session/shelf-session")
        assert audit.status_code == 200
        event = next(event for event in audit.json()["events"] if event["event_type"] == "shelf_image_analysis_created")
        assert event["payload_json"]["grounded_alert_ids"] == [alert["alert_id"]]
