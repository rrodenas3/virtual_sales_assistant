from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.osa import OSADataPort
from backend.agents.graph import run_osa_summary_graph
from backend.agents.state import AgentState
from backend.api.schemas import OSASummaryRequest, OSASummaryResponse
from backend.auth.mock_jwt import CurrentUser
from backend.config import settings
from backend.governance.guardrails import check_guardrails
from backend.governance.rbac import assert_territory_access
from backend.memory.adapters import get_memory_adapter
from backend.services.audit import log_audit_event
from backend.services.summary_providers import (
    SummaryGroundingError,
    SummaryProviderError,
    TemplateSummaryProvider,
    get_summary_provider,
)
from backend.services.telemetry import log_structured_event


class SummaryValidationError(ValueError):
    pass


class SummaryGuardrailError(ValueError):
    pass


async def create_osa_summary(
    db: AsyncSession,
    osa: OSADataPort,
    current_user: CurrentUser,
    request: OSASummaryRequest,
) -> OSASummaryResponse:
    assert_territory_access(current_user, request.territory_code)
    guardrail = check_guardrails(" ".join(request.alert_ids or []))
    if guardrail.blocked:
        raise SummaryGuardrailError(guardrail.reason)

    orchestration_mode = "graph" if settings.agent_graph_enabled else "service"
    if settings.agent_graph_enabled:
        graph_state = AgentState(
            session_id=request.session_id,
            rep_id=current_user.rep_id,
            role=current_user.role,
            territory_code=request.territory_code,
            store_id=request.store_id,
            alert_ids=request.alert_ids,
        )
        try:
            graph_state = await run_osa_summary_graph(graph_state, osa)
        except ValueError as exc:
            raise SummaryValidationError(str(exc)) from exc
        alerts = graph_state.alerts
    else:
        alerts = await osa.get_alerts_by_ids(current_user.rep_id, request.territory_code, request.alert_ids)
        if request.alert_ids is not None and len(alerts) != len(set(request.alert_ids)):
            raise SummaryValidationError("Unknown alert_id in grounded set")
        if request.store_id:
            alerts = [alert for alert in alerts if alert.store_id == request.store_id]

    memory = get_memory_adapter()
    memory_context = await memory.get_context(rep_id=current_user.rep_id, store_id=request.store_id)
    memory_count = len(memory_context.get("memories", []))
    try:
        summary_result = await get_summary_provider().summarize(alerts)
    except SummaryGroundingError as exc:
        raise SummaryValidationError(str(exc)) from exc
    except SummaryProviderError as exc:
        if not settings.summary_fail_open:
            raise SummaryValidationError(str(exc)) from exc
        summary_result = await TemplateSummaryProvider().summarize(alerts)
        summary_result = summary_result.__class__(
            **{**summary_result.__dict__, "fallback_used": True, "grounding_result": "provider_fallback"}
        )

    event = await log_audit_event(
        db,
        session_id=request.session_id,
        rep_id=current_user.rep_id,
        event_type="osa_summary_created",
        resource_type="agent_summary",
        resource_id=request.store_id or request.territory_code,
        payload_json={
            "grounded_alert_ids": [alert.alert_id for alert in alerts],
            "model_id": summary_result.model_id,
            "summary_provider": summary_result.provider,
            "estimated_input_tokens": summary_result.estimated_input_tokens,
            "estimated_output_tokens": summary_result.estimated_output_tokens,
            "estimated_cost_eur": summary_result.estimated_cost_eur,
            "latency_ms": summary_result.latency_ms,
            "grounding_result": summary_result.grounding_result,
            "fallback_used": summary_result.fallback_used,
            "orchestration_mode": orchestration_mode,
            "memory_provider": memory_context.get("provider", "none"),
            "memory_count": memory_count,
        },
        data_freshness_ts=alerts[0].data_freshness_ts if alerts else None,
    )
    await db.commit()
    log_structured_event(
        "osa_summary_created",
        audit_event_id=event.event_id,
        rep_id=current_user.rep_id,
        session_id=request.session_id,
        model_id=summary_result.model_id,
        summary_provider=summary_result.provider,
        grounded_alert_count=len(alerts),
        estimated_input_tokens=summary_result.estimated_input_tokens,
        estimated_output_tokens=summary_result.estimated_output_tokens,
        estimated_cost_eur=summary_result.estimated_cost_eur,
        latency_ms=summary_result.latency_ms,
        fallback_used=summary_result.fallback_used,
        orchestration_mode=orchestration_mode,
        memory_provider=memory_context.get("provider", "none"),
        memory_count=memory_count,
    )
    try:
        await memory.record_interaction(
            rep_id=current_user.rep_id,
            session_id=request.session_id,
            payload={
                "event_type": "osa_summary_created",
                "store_id": request.store_id,
                "summary": summary_result.summary,
                "audit_event_id": event.event_id,
                "grounded_alert_count": len(alerts),
            },
        )
    except Exception as exc:  # pragma: no cover - telemetry-only degradation path
        log_structured_event(
            "memory_record_failed",
            audit_event_id=event.event_id,
            rep_id=current_user.rep_id,
            session_id=request.session_id,
            memory_provider=memory_context.get("provider", "none"),
            error_type=type(exc).__name__,
        )
    return OSASummaryResponse(
        summary=summary_result.summary,
        grounded_alert_ids=[alert.alert_id for alert in alerts],
        session_id=request.session_id,
        model_id=summary_result.model_id,
        audit_event_id=event.event_id,
    )
