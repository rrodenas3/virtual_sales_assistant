from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.osa import OSADataPort
from backend.api.schemas import OfflineFeedbackSyncItem, OfflineFeedbackSyncRequest, OfflineFeedbackSyncResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.models import IdempotencyRecord
from backend.db.session import get_db
from backend.deps import get_osa_adapter
from backend.services.feedback import create_alert_feedback

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/feedback-events", response_model=OfflineFeedbackSyncResponse)
async def sync_feedback_events(
    request: OfflineFeedbackSyncRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> OfflineFeedbackSyncResponse:
    results: list[OfflineFeedbackSyncItem] = []
    for event in request.events:
        if not event.idempotency_key.startswith(f"{current_user.rep_id}:"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid idempotency key")

        existing = await db.get(IdempotencyRecord, event.idempotency_key)
        if existing:
            results.append(
                OfflineFeedbackSyncItem(
                    idempotency_key=event.idempotency_key,
                    status="duplicate",
                    feedback=existing.response_json["feedback"],
                )
            )
            continue

        feedback = await create_alert_feedback(
            db=db,
            osa=osa,
            current_user=current_user,
            alert_id=event.alert_id,
            feedback_value=event.feedback,
            session_id=event.session_id,
            notes=event.notes,
        )
        if not feedback:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

        record = IdempotencyRecord(
            idempotency_key=event.idempotency_key,
            rep_id=current_user.rep_id,
            event_type="offline_feedback",
            response_json={"feedback": feedback.model_dump(mode="json")},
        )
        db.add(record)
        results.append(
            OfflineFeedbackSyncItem(
                idempotency_key=event.idempotency_key,
                status="created",
                feedback=feedback,
            )
        )

    await db.commit()
    return OfflineFeedbackSyncResponse(results=results)
