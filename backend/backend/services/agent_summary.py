from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.osa import OSADataPort
from backend.api.schemas import OSASummaryRequest, OSASummaryResponse
from backend.auth.mock_jwt import CurrentUser
from backend.config import settings
from backend.governance.guardrails import check_guardrails
from backend.governance.rbac import assert_territory_access
from backend.services.audit import log_audit_event
from backend.services.summary import build_grounded_summary
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

    alerts = await osa.get_alerts_by_ids(current_user.rep_id, request.territory_code, request.alert_ids)
    if request.alert_ids is not None and len(alerts) != len(set(request.alert_ids)):
        raise SummaryValidationError("Unknown alert_id in grounded set")
    if request.store_id:
        alerts = [alert for alert in alerts if alert.store_id == request.store_id]

    summary = build_grounded_summary(alerts)
    estimated_input_tokens = max(1, sum(len(alert.model_dump_json()) for alert in alerts) // 4)
    estimated_output_tokens = max(1, len(summary) // 4)
    estimated_cost_eur = round((estimated_input_tokens + estimated_output_tokens) * 0.000002, 6)
    event = await log_audit_event(
        db,
        session_id=request.session_id,
        rep_id=current_user.rep_id,
        event_type="osa_summary_created",
        resource_type="agent_summary",
        resource_id=request.store_id or request.territory_code,
        payload_json={
            "grounded_alert_ids": [alert.alert_id for alert in alerts],
            "model_id": settings.llm_model_id,
            "estimated_input_tokens": estimated_input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "estimated_cost_eur": estimated_cost_eur,
        },
        data_freshness_ts=alerts[0].data_freshness_ts if alerts else None,
    )
    await db.commit()
    log_structured_event(
        "osa_summary_created",
        audit_event_id=event.event_id,
        rep_id=current_user.rep_id,
        session_id=request.session_id,
        model_id=settings.llm_model_id,
        grounded_alert_count=len(alerts),
        estimated_input_tokens=estimated_input_tokens,
        estimated_output_tokens=estimated_output_tokens,
        estimated_cost_eur=estimated_cost_eur,
    )
    return OSASummaryResponse(
        summary=summary,
        grounded_alert_ids=[alert.alert_id for alert in alerts],
        session_id=request.session_id,
        model_id=settings.llm_model_id,
        audit_event_id=event.event_id,
    )
