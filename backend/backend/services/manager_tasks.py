from __future__ import annotations


def manager_task_payload(*, notes: str | None, linked_alert_ids: list[str] | None = None) -> dict:
    return {
        "notes": notes,
        "linked_alert_ids": linked_alert_ids or [],
    }


def manager_task_status_payload(
    existing_payload: dict,
    *,
    notes: str | None,
    updated_by: str,
    previous_status: str,
) -> dict:
    payload = dict(existing_payload)
    payload["status_notes"] = notes
    payload["status_updated_by"] = updated_by
    payload["previous_status"] = previous_status
    return payload
