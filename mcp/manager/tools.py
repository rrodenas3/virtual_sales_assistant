from __future__ import annotations

from backend.services.manager_tasks import manager_task_payload, manager_task_status_payload


def preview_manager_task_payload(
    territory_code: str,
    store_id: str,
    assigned_rep_id: str,
    created_by: str,
    session_id: str,
    title: str,
    task_type: str,
    priority: str,
    due_date: str | None = None,
    notes: str | None = None,
    linked_alert_ids: list[str] | None = None,
) -> dict:
    return {
        "territory_code": territory_code,
        "store_id": store_id,
        "assigned_rep_id": assigned_rep_id,
        "created_by": created_by,
        "session_id": session_id,
        "title": title,
        "task_type": task_type,
        "priority": priority,
        "due_date": due_date,
        "payload_json": manager_task_payload(notes=notes, linked_alert_ids=linked_alert_ids),
        "status": "OPEN",
        "requires_approval": False,
        "submit_path": "POST /api/v1/manager/tasks",
    }


def preview_manager_task_status_update(
    task_id: str,
    updated_by: str,
    previous_status: str,
    next_status: str,
    session_id: str,
    existing_payload: dict | None = None,
    notes: str | None = None,
) -> dict:
    return {
        "task_id": task_id,
        "updated_by": updated_by,
        "session_id": session_id,
        "previous_status": previous_status,
        "next_status": next_status,
        "payload_json": manager_task_status_payload(
            existing_payload or {},
            notes=notes,
            updated_by=updated_by,
            previous_status=previous_status,
        ),
        "requires_approval": False,
        "submit_path": "POST /api/v1/manager/tasks/{task_id}/status",
    }
