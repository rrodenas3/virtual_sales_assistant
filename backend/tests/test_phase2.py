from fastapi.testclient import TestClient

from backend.main import app


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."
REP_002 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAyIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def authorized_client(token: str = REP_001) -> TestClient:
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


def test_rgm_recommendations_are_scoped_and_audited() -> None:
    with authorized_client() as c:
        response = c.get("/api/v1/stores/ST-001/rgm-recommendations")
        assert response.status_code == 200
        body = response.json()
        assert body["store_id"] == "ST-001"
        assert body["promos"]
        assert body["assortment_gaps"]
        assert body["upsell_opportunities"]
        assert body["audit_event_id"]

    with authorized_client(REP_002) as c:
        response = c.get("/api/v1/stores/ST-001/rgm-recommendations")
        assert response.status_code == 404


def test_order_draft_approval_records_payload_hash_and_blocks_reapproval() -> None:
    with authorized_client() as c:
        draft = c.post(
            "/api/v1/orders/drafts",
            json={
                "store_id": "ST-001",
                "session_id": "phase2-order-test",
                "items": [
                    {
                        "sku_id": "SKU-4001",
                        "sku_name": "Core SKU 4001",
                        "quantity": 12,
                        "reason": "High OOS risk",
                    }
                ],
                "notes": "Pilot draft",
            },
        )
        assert draft.status_code == 200
        draft_body = draft.json()
        assert draft_body["status"] == "DRAFT"
        assert len(draft_body["payload_hash"]) == 64

        approval = c.post(
            f"/api/v1/approvals/{draft_body['draft_id']}/approve",
            json={"notes": "Approved in pilot"},
        )
        assert approval.status_code == 200
        approval_body = approval.json()
        assert approval_body["approved"] is True
        assert approval_body["draft_payload_hash"] == draft_body["payload_hash"]
        assert approval_body["audit_event_id"]

        refreshed = c.get(f"/api/v1/orders/drafts/{draft_body['draft_id']}")
        assert refreshed.status_code == 200
        assert refreshed.json()["status"] == "APPROVED"

        repeat = c.post(f"/api/v1/approvals/{draft_body['draft_id']}/approve", json={"notes": "again"})
        assert repeat.status_code == 409


def test_order_draft_is_hidden_from_other_reps() -> None:
    with authorized_client() as c:
        draft = c.post(
            "/api/v1/orders/drafts",
            json={
                "store_id": "ST-001",
                "session_id": "phase2-hidden-test",
                "items": [
                    {
                        "sku_id": "SKU-4002",
                        "sku_name": "Core SKU 4002",
                        "quantity": 6,
                        "reason": "Follow-up order",
                    }
                ],
            },
        ).json()

    with authorized_client(REP_002) as c:
        response = c.get(f"/api/v1/orders/drafts/{draft['draft_id']}")
        assert response.status_code == 404


def test_crm_visit_log_draft_is_created_and_audited() -> None:
    with authorized_client() as c:
        response = c.post(
            "/api/v1/crm/visit-log-drafts",
            json={
                "store_id": "ST-001",
                "session_id": "phase2-crm-test",
                "notes": "Shelf check complete; two OOS risks confirmed.",
                "outcome": "completed",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "DRAFT"
        assert body["payload_json"]["outcome"] == "completed"
        assert body["audit_event_id"]

