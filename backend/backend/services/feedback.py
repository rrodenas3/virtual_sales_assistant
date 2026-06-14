from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.osa import OSADataPort
from backend.api.schemas import AlertFeedbackResponse, FeedbackValue
from backend.auth.mock_jwt import CurrentUser
from backend.db.models import AlertFeedback
from backend.services.audit import log_audit_event


async def create_alert_feedback(
    *,
    db: AsyncSession,
    osa: OSADataPort,
    current_user: CurrentUser,
    alert_id: str,
    feedback_value: FeedbackValue,
    session_id: str,
    notes: str | None,
) -> AlertFeedbackResponse | None:
    if not current_user.territory_code:
        return None
    matches = await osa.get_alerts_by_ids(current_user.rep_id, current_user.territory_code, [alert_id])
    if not matches:
        return None
    alert = matches[0]
    feedback = AlertFeedback(
        alert_id=alert.alert_id,
        store_id=alert.store_id,
        sku_id=alert.sku_id,
        rep_id=current_user.rep_id,
        feedback=feedback_value,
        notes=notes,
        session_id=session_id,
    )
    db.add(feedback)
    await db.flush()
    event = await log_audit_event(
        db,
        session_id=session_id,
        rep_id=current_user.rep_id,
        event_type="alert_feedback_created",
        resource_type="alert",
        resource_id=alert.alert_id,
        payload_json={"feedback": feedback_value, "notes_present": notes is not None},
        data_freshness_ts=alert.data_freshness_ts,
    )
    await db.flush()
    return AlertFeedbackResponse(
        id=feedback.id,
        alert_id=feedback.alert_id,
        store_id=feedback.store_id,
        sku_id=feedback.sku_id,
        rep_id=feedback.rep_id,
        feedback=feedback.feedback,  # type: ignore[arg-type]
        notes=feedback.notes,
        session_id=feedback.session_id,
        created_at=feedback.created_at,
        audit_event_id=event.event_id,
    )
