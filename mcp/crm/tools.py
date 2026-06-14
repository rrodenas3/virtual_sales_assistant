from __future__ import annotations


def preview_visit_log_draft(store_id: str, rep_id: str, session_id: str, notes: str, outcome: str) -> dict:
    return {
        "store_id": store_id,
        "rep_id": rep_id,
        "session_id": session_id,
        "payload_json": {"notes": notes, "outcome": outcome},
        "status": "DRAFT",
        "requires_approval": False,
        "submit_path": "POST /api/v1/crm/visit-log-drafts",
    }
