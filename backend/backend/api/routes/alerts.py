from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.osa import OSADataPort
from backend.api.schemas import AlertFeedbackRequest, AlertFeedbackResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.session import get_db
from backend.deps import get_osa_adapter
from backend.services.feedback import create_alert_feedback

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/{alert_id}/feedback", response_model=AlertFeedbackResponse)
async def submit_feedback(
    alert_id: str,
    request: AlertFeedbackRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> AlertFeedbackResponse:
    feedback = await create_alert_feedback(
        db=db,
        osa=osa,
        current_user=current_user,
        alert_id=alert_id,
        feedback_value=request.feedback,
        session_id=request.session_id,
        notes=request.notes,
    )
    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    await db.commit()
    return feedback
