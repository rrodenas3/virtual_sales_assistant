import pytest

from backend.adapters.factory import get_osa_data_port
from backend.agents.graph import order_hitl_node, run_osa_summary_graph, visit_priority_node
from backend.agents.state import AgentState
from backend.services.summary import build_grounded_summary


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
