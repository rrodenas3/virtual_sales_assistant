from __future__ import annotations

from backend.services.hashing import stable_payload_hash


def preview_order_draft_payload(store_id: str, rep_id: str, items: list[dict], notes: str | None = None) -> dict:
    payload = {
        "store_id": store_id,
        "rep_id": rep_id,
        "items": items,
        "notes": notes,
    }
    return {
        "payload_json": payload,
        "payload_hash": stable_payload_hash(payload),
        "requires_approval": True,
        "submit_path": "POST /api/v1/orders/drafts",
    }
