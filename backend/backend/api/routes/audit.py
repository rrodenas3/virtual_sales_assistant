from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import AlertFeedbackResponse, AuditEventOut, AuditSessionResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.session import get_db
from backend.services.audit import get_session_audit

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/session/{session_id}", response_model=AuditSessionResponse)
async def audit_session(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditSessionResponse:
    events, feedback = await get_session_audit(db, session_id)
    visible_events = [event for event in events if current_user.role == "admin" or event.rep_id == current_user.rep_id]
    visible_feedback = [item for item in feedback if current_user.role == "admin" or item.rep_id == current_user.rep_id]
    return AuditSessionResponse(
        session_id=session_id,
        events=[
            AuditEventOut(
                event_id=event.event_id,
                session_id=event.session_id,
                rep_id=event.rep_id,
                event_type=event.event_type,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                payload_json=event.payload_json,
                source_system=event.source_system,
                data_freshness_ts=event.data_freshness_ts,
                created_at=event.created_at,
            )
            for event in visible_events
        ],
        feedback=[
            AlertFeedbackResponse(
                id=item.id,
                alert_id=item.alert_id,
                store_id=item.store_id,
                sku_id=item.sku_id,
                rep_id=item.rep_id,
                feedback=item.feedback,  # type: ignore[arg-type]
                notes=item.notes,
                session_id=item.session_id,
                created_at=item.created_at,
                audit_event_id="",
            )
            for item in visible_feedback
        ],
    )

