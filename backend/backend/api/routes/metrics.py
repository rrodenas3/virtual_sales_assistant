from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import PilotMetric, PilotMetricsResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.models import AlertFeedback, AuditEvent
from backend.db.session import get_db

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/pilot", response_model=PilotMetricsResponse)
async def pilot_metrics(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PilotMetricsResponse:
    feedback_rows = list((await db.execute(select(AlertFeedback))).scalars())
    audit_rows = list((await db.execute(select(AuditEvent))).scalars())

    if current_user.role != "admin":
        feedback_rows = [row for row in feedback_rows if row.rep_id == current_user.rep_id]
        audit_rows = [row for row in audit_rows if row.rep_id == current_user.rep_id]

    confirmed = len([row for row in feedback_rows if row.feedback == "confirmed"])
    false_positive = len([row for row in feedback_rows if row.feedback == "false_positive"])
    precision_denominator = confirmed + false_positive
    precision = confirmed / precision_denominator if precision_denominator else None

    event_counts: dict[str, int] = {}
    for event in audit_rows:
        event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1

    summary_events = [event for event in audit_rows if event.event_type == "osa_summary_created"]
    costs = [
        float(event.payload_json["estimated_cost_eur"])
        for event in summary_events
        if "estimated_cost_eur" in event.payload_json
    ]
    avg_cost = sum(costs) / len(costs) if costs else None

    metrics = [
        PilotMetric(name="OSA alert precision", value=precision or 0.0, unit="ratio"),
        PilotMetric(name="Confirmed alerts", value=float(confirmed), unit="count"),
        PilotMetric(name="Summary interactions", value=float(len(summary_events)), unit="count"),
        PilotMetric(name="Average summary cost", value=avg_cost or 0.0, unit="EUR"),
    ]
    return PilotMetricsResponse(
        feedback_count=len(feedback_rows),
        confirmed_count=confirmed,
        false_positive_count=false_positive,
        alert_precision=precision,
        summary_count=len(summary_events),
        avg_estimated_cost_eur=avg_cost,
        trace_event_counts=event_counts,
        metrics=metrics,
    )
