from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.crm import CRMPort
from backend.adapters.osa import OSADataPort
from backend.api.schemas import VisitLogDraftRequest, VisitLogDraftResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.session import get_db
from backend.deps import get_crm_adapter, get_osa_adapter
from backend.services.agent_actions import AgentActionNotFound, create_visit_log_draft_action

router = APIRouter(prefix="/crm", tags=["crm"])


def _http_error_for_action(exc: ValueError) -> HTTPException:
    if isinstance(exc, AgentActionNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/visit-log-drafts", response_model=VisitLogDraftResponse)
async def create_visit_log_draft(
    request: VisitLogDraftRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
    crm: CRMPort = Depends(get_crm_adapter),
) -> VisitLogDraftResponse:
    try:
        return await create_visit_log_draft_action(db, osa, crm, current_user, request)
    except ValueError as exc:
        raise _http_error_for_action(exc) from exc

