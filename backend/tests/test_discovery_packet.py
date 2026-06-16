from fastapi.testclient import TestClient

from backend.config import settings
from backend.governance.discovery_packet import build_discovery_packet
from backend.main import app

REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."
MANAGER = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJNR1ItMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6Im1hbmFnZXIifQ."


def test_discovery_packet_endpoint_requires_manager_or_admin() -> None:
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/integrations/discovery-packet?target=pilot")
    assert response.status_code == 403


def test_discovery_packet_endpoint_groups_pilot_questions_by_owner() -> None:
    with TestClient(app, headers={"Authorization": f"Bearer {MANAGER}"}) as client:
        response = client.get("/api/v1/integrations/discovery-packet?target=pilot")
    assert response.status_code == 200
    body = response.json()
    assert body["target"] == "pilot"
    assert body["gate_count"] >= 10
    assert body["missing_count"] >= 7
    assert body["defaulted_count"] >= 2
    assert body["public_safety_notes"]
    owners = {group["owner"]: group for group in body["owner_groups"]}
    assert "delivery" in owners
    assert "shared" in owners
    assert owners["delivery"]["missing_count"] >= 6
    assert any(gate["setting_name"] == "discovery_sso_provider" for gate in owners["delivery"]["gates"])
    assert all("value" not in gate for group in body["owner_groups"] for gate in group["gates"])
    assert body["next_actions"][0].startswith("delivery: answer")


def test_discovery_packet_marks_answered_without_exposing_values(monkeypatch) -> None:
    monkeypatch.setattr(settings, "discovery_data_sharing_model", "client-databricks")
    packet = build_discovery_packet("pilot")
    gates = [gate for group in packet["owner_groups"] for gate in group["gates"]]
    data_gate = next(gate for gate in gates if gate["setting_name"] == "discovery_data_sharing_model")
    assert data_gate["status"] == "answered"
    assert data_gate["value_present"] is True
    assert "client-databricks" not in str(packet)
