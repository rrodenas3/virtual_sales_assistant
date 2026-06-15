import base64
import json

from fastapi.testclient import TestClient

from backend.main import app


def token(claims: dict) -> str:
    def enc(data: dict) -> str:
        raw = json.dumps(data, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{enc({'alg': 'none', 'typ': 'JWT'})}.{enc(claims)}."


REP_001 = token({"sub": "REP-001", "territory_code": "WEST-01", "role": "rep"})
MANAGER = token({"sub": "MGR-001", "territory_code": "WEST-01", "role": "manager"})
ADMIN = token({"sub": "ADMIN-001", "role": "admin"})


def authorized_client(jwt: str) -> TestClient:
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {jwt}"})
    return c


def test_manager_can_read_territory_summary_and_store_alerts() -> None:
    with authorized_client(MANAGER) as c:
        summary = c.get("/api/v1/manager/territory-summary?territory_code=WEST-01")
        assert summary.status_code == 200
        body = summary.json()
        assert body["store_count"] == 25
        assert body["total_oos_alerts"] >= 100

        alerts = c.get("/api/v1/stores/ST-001/alerts")
        assert alerts.status_code == 200
        assert alerts.json()["alerts"]


def test_rep_cannot_read_manager_summary() -> None:
    with authorized_client(REP_001) as c:
        summary = c.get("/api/v1/manager/territory-summary?territory_code=WEST-01")
        assert summary.status_code == 403


def test_admin_audit_requires_admin_role() -> None:
    with authorized_client(REP_001) as c:
        forbidden = c.get("/api/v1/admin/audit-events")
        assert forbidden.status_code == 403

    with authorized_client(ADMIN) as c:
        allowed = c.get("/api/v1/admin/audit-events")
        assert allowed.status_code == 200
        assert "events" in allowed.json()


def test_manager_approval_queue_lists_and_can_approve_territory_drafts() -> None:
    with authorized_client(REP_001) as rep:
        alert = rep.get("/api/v1/stores/ST-001/alerts").json()["alerts"][0]
        draft_response = rep.post(
            "/api/v1/orders/drafts",
            json={
                "store_id": "ST-001",
                "session_id": "manager-queue-test",
                "items": [
                    {
                        "sku_id": alert["sku_id"],
                        "sku_name": alert["sku_name"],
                        "quantity": 12,
                        "reason": alert["recommended_action"],
                    }
                ],
                "notes": "manager queue test",
            },
        )
        assert draft_response.status_code == 200
        draft = draft_response.json()

    with authorized_client(MANAGER) as manager:
        queue = manager.get("/api/v1/manager/approval-queue?territory_code=WEST-01")
        assert queue.status_code == 200
        body = queue.json()
        assert any(item["draft_id"] == draft["draft_id"] for item in body["items"])

        approval = manager.post(f"/api/v1/approvals/{draft['draft_id']}/approve", json={"notes": "manager ok"})
        assert approval.status_code == 200
        assert approval.json()["approved_by"] == "MGR-001"


def test_manager_can_create_task_and_rep_can_read_assignment() -> None:
    with authorized_client(MANAGER) as manager:
        created = manager.post(
            "/api/v1/manager/tasks",
            json={
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "assigned_rep_id": "REP-001",
                "session_id": "manager_task_test",
                "title": "Verify shelf before noon",
                "task_type": "shelf_check",
                "priority": "high",
                "due_date": "2026-06-16",
                "notes": "Check top two risk SKUs.",
                "linked_alert_ids": [],
            },
        )
        assert created.status_code == 200
        task = created.json()
        assert task["created_by"] == "MGR-001"
        assert task["status"] == "OPEN"
        assert task["audit_event_id"]

        listed = manager.get("/api/v1/manager/tasks?territory_code=WEST-01")
        assert listed.status_code == 200
        assert any(row["task_id"] == task["task_id"] for row in listed.json()["tasks"])

        audit = manager.get("/api/v1/audit/session/manager_task_test")
        assert audit.status_code == 200
        assert any(event["event_type"] == "manager_task_created" for event in audit.json()["events"])

    with authorized_client(REP_001) as rep:
        mine = rep.get("/api/v1/manager/my-tasks")
        assert mine.status_code == 200
        assert any(row["task_id"] == task["task_id"] for row in mine.json()["tasks"])

        completed = rep.post(
            f"/api/v1/manager/tasks/{task['task_id']}/status",
            json={"status": "COMPLETED", "session_id": "manager_task_complete", "notes": "Shelf verified."},
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "COMPLETED"
        assert completed.json()["audit_event_id"]

        forbidden = rep.post(
            f"/api/v1/manager/tasks/{task['task_id']}/status",
            json={"status": "CANCELLED", "session_id": "manager_task_cancel_forbidden"},
        )
        assert forbidden.status_code == 403


def test_manager_can_cancel_territory_task() -> None:
    with authorized_client(MANAGER) as manager:
        created = manager.post(
            "/api/v1/manager/tasks",
            json={
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "assigned_rep_id": "REP-001",
                "session_id": "manager_task_cancel_create",
                "title": "Cancel this duplicate task",
                "task_type": "follow_up",
                "priority": "low",
            },
        )
        assert created.status_code == 200
        task = created.json()

        cancelled = manager.post(
            f"/api/v1/manager/tasks/{task['task_id']}/status",
            json={"status": "CANCELLED", "session_id": "manager_task_cancel", "notes": "Duplicate task."},
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "CANCELLED"

        blocked = manager.post(
            f"/api/v1/manager/tasks/{task['task_id']}/status",
            json={"status": "COMPLETED", "session_id": "manager_task_complete_forbidden"},
        )
        assert blocked.status_code == 403


def test_rep_cannot_create_manager_task() -> None:
    with authorized_client(REP_001) as rep:
        response = rep.post(
            "/api/v1/manager/tasks",
            json={
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "assigned_rep_id": "REP-001",
                "session_id": "manager_task_forbidden",
                "title": "Verify shelf",
                "task_type": "shelf_check",
                "priority": "medium",
            },
        )
        assert response.status_code == 403


def test_admin_audit_filters_and_detail_endpoint() -> None:
    with authorized_client(REP_001) as rep:
        response = rep.get("/api/v1/visits/today?territory_code=WEST-01&date=2026-06-14")
        assert response.status_code == 200

    with authorized_client(ADMIN) as admin:
        filtered = admin.get("/api/v1/admin/audit-events?event_type=visit_priority_read&rep_id=REP-001&limit=1")
        assert filtered.status_code == 200
        body = filtered.json()
        assert body["events"]
        assert body["events"][0]["event_type"] == "visit_priority_read"
        assert body["events"][0]["rep_id"] == "REP-001"
        assert "next_cursor" in body

        detail = admin.get(f"/api/v1/admin/audit-events/{body['events'][0]['event_id']}")
        assert detail.status_code == 200
        assert detail.json()["event"]["event_id"] == body["events"][0]["event_id"]
