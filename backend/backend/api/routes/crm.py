from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.osa import OSADataPort
from backend.api.schemas import VisitLogDraftRequest, VisitLogDraftResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.models import VisitLog
from backend.db.session import get_db
from backend.deps import get_osa_adapter
from backend.governance.rbac import assert_store_access
from backend.services.audit import log_audit_event

router = APIRouter(prefix="/crm", tags=["crm"])


@router.post("/visit-log-drafts", response_model=VisitLogDraftResponse)
async def create_visit_log_draft(
    request: VisitLogDraftRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> VisitLogDraftResponse:
    try:
        store = await osa.get_store_detail(current_user.rep_id, request.store_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found") from exc
    assert_store_access(current_user, store.rep_id, store.territory_code)
    payload = {"notes": request.notes, "outcome": request.outcome}
    draft = VisitLog(
        store_id=request.store_id,
        rep_id=current_user.rep_id,
        session_id=request.session_id,
        payload_json=payload,
        status="DRAFT",
    )
    db.add(draft)
    await db.flush()
    event = await log_audit_event(
        db,
        session_id=request.session_id,
        rep_id=current_user.rep_id,
        event_type="crm_visit_log_draft_created",
        resource_type="visit_log",
        resource_id=draft.id,
        payload_json={"status": draft.status, "outcome": request.outcome},
        data_freshness_ts=store.data_freshness_ts,
    )
    await db.commit()
    await db.refresh(draft)
    return VisitLogDraftResponse(
        id=draft.id,
        store_id=draft.store_id,
        rep_id=draft.rep_id,
        session_id=draft.session_id,
        payload_json=draft.payload_json,
        status=draft.status,
        created_at=draft.created_at,
        audit_event_id=event.event_id,
    )

