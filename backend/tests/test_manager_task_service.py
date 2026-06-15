from backend.services.manager_tasks import manager_task_payload, manager_task_status_payload


def test_manager_task_payload_helpers_are_stable() -> None:
    payload = manager_task_payload(notes="Check shelf", linked_alert_ids=["alert_1"])

    assert payload == {"notes": "Check shelf", "linked_alert_ids": ["alert_1"]}

    updated = manager_task_status_payload(
        payload,
        notes="Done",
        updated_by="REP-001",
        previous_status="OPEN",
    )

    assert updated["notes"] == "Check shelf"
    assert updated["linked_alert_ids"] == ["alert_1"]
    assert updated["status_notes"] == "Done"
    assert updated["status_updated_by"] == "REP-001"
    assert updated["previous_status"] == "OPEN"
