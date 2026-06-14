from __future__ import annotations

from datetime import date

from backend.adapters.osa import OSADataPort
from backend.agents.state import AgentState, HITLState
from backend.services.summary import build_grounded_summary


async def visit_priority_node(state: AgentState, osa: OSADataPort) -> AgentState:
    visit_date = state.visit_date or date.today()
    visits = await osa.get_visit_priority(state.rep_id, state.territory_code, visit_date)
    return state.model_copy(update={"visit_date": visit_date, "visits": visits})


async def grounded_alerts_node(state: AgentState, osa: OSADataPort) -> AgentState:
    alerts = await osa.get_alerts_by_ids(state.rep_id, state.territory_code, state.alert_ids)
    if state.alert_ids is not None and len(alerts) != len(set(state.alert_ids)):
        raise ValueError("Unknown alert_id in grounded set")
    if state.store_id:
        alerts = [alert for alert in alerts if alert.store_id == state.store_id]
    return state.model_copy(update={"alerts": alerts})


async def summary_node(state: AgentState) -> AgentState:
    return state.model_copy(update={"summary": build_grounded_summary(state.alerts)})


async def order_hitl_node(state: AgentState, reason: str = "order_draft_requires_human_approval") -> AgentState:
    token = f"{state.session_id}:hitl:order"
    return state.model_copy(update={"hitl": HITLState(required=True, reason=reason, resume_token=token)})


async def run_osa_summary_graph(state: AgentState, osa: OSADataPort) -> AgentState:
    state = await grounded_alerts_node(state, osa)
    return await summary_node(state)
