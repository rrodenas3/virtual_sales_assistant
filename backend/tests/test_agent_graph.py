import pytest

from backend.adapters.factory import get_osa_data_port
from backend.agents.graph import order_hitl_node, run_osa_summary_graph, visit_priority_node
from backend.agents.state import AgentState
from backend.services.summary import build_grounded_summary
from backend.config import settings
from backend.main import app
from fastapi.testclient import TestClient


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def authorized_client() -> TestClient:
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {REP_001}"})
    return c


@pytest.mark.asyncio
async def test_visit_priority_graph_node_matches_adapter() -> None:
    osa = get_osa_data_port()
    state = AgentState(session_id="graph-visits", rep_id="REP-001", territory_code="WEST-01")
    result = await visit_priority_node(state, osa)
    direct = await osa.get_visit_priority("REP-001", "WEST-01", result.visit_date)
    assert [row.store_id for row in result.visits] == [row.store_id for row in direct]


@pytest.mark.asyncio
async def test_osa_summary_graph_matches_summary_service() -> None:
    osa = get_osa_data_port()
    alerts = await osa.get_alerts_by_ids("REP-001", "WEST-01", None)
    alert_ids = [alert.alert_id for alert in alerts[:2]]
    state = AgentState(
        session_id="graph-summary",
        rep_id="REP-001",
        territory_code="WEST-01",
        store_id=alerts[0].store_id,
        alert_ids=alert_ids,
    )
    result = await run_osa_summary_graph(state, osa)
    assert result.summary == build_grounded_summary(result.alerts)
    assert {alert.alert_id for alert in result.alerts} <= set(alert_ids)


@pytest.mark.asyncio
async def test_order_hitl_node_marks_interrupt_state() -> None:
    state = AgentState(session_id="graph-hitl", rep_id="REP-001", territory_code="WEST-01")
    result = await order_hitl_node(state)
    assert result.hitl.required is True
    assert result.hitl.resume_token == "graph-hitl:hitl:order"


def test_osa_summary_route_uses_graph_when_feature_flag_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "agent_graph_enabled", True)
    with authorized_client() as c:
        alerts = c.get("/api/v1/stores/ST-001/alerts").json()["alerts"][:2]
        response = c.post(
            "/api/v1/agent/osa-summary",
            json={
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "session_id": "graph-route-test",
                "alert_ids": [alert["alert_id"] for alert in alerts],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert set(body["grounded_alert_ids"]) == {alert["alert_id"] for alert in alerts}

        audit = c.get("/api/v1/audit/session/graph-route-test")
        assert audit.status_code == 200
        summary_events = [event for event in audit.json()["events"] if event["event_type"] == "osa_summary_created"]
        assert summary_events
        assert summary_events[-1]["payload_json"]["orchestration_mode"] == "graph"


def test_graph_and_service_summary_routes_return_same_grounded_output(monkeypatch) -> None:
    with authorized_client() as c:
        alerts = c.get("/api/v1/stores/ST-001/alerts").json()["alerts"][:2]
        payload = {
            "territory_code": "WEST-01",
            "store_id": "ST-001",
            "session_id": "service-route-test",
            "alert_ids": [alert["alert_id"] for alert in alerts],
        }

        monkeypatch.setattr(settings, "agent_graph_enabled", False)
        service_body = c.post("/api/v1/agent/osa-summary", json=payload).json()

        monkeypatch.setattr(settings, "agent_graph_enabled", True)
        graph_body = c.post(
            "/api/v1/agent/osa-summary",
            json={**payload, "session_id": "graph-parity-route-test"},
        ).json()

        assert graph_body["summary"] == service_body["summary"]
        assert graph_body["grounded_alert_ids"] == service_body["grounded_alert_ids"]
