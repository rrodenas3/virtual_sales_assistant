from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.routes.orders import get_draft_for_approval
from backend.api.schemas import ApprovalRequest, ApprovalResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.models import ApprovalRecord
from backend.db.session import get_db
from backend.services.audit import log_audit_event

router = APIRouter(prefix="/approvals", tags=["approvals"])


async def _record_decision(
    draft_id: str,
    approved: bool,
    request: ApprovalRequest,
    current_user: CurrentUser,
    db: AsyncSession,
) -> ApprovalResponse:
    draft = await get_draft_for_approval(db, draft_id, current_user)
    approval = ApprovalRecord(
        draft_id=draft.draft_id,
        approved=approved,
        approved_by=current_user.rep_id,
        notes=request.notes,
        draft_payload_hash=draft.payload_hash,
    )
    db.add(approval)
    await db.flush()
    draft.status = "APPROVED" if approved else "REJECTED"
    event = await log_audit_event(
        db,
        session_id=draft.session_id,
        rep_id=current_user.rep_id,
        event_type="order_draft_approved" if approved else "order_draft_rejected",
        resource_type="order_draft",
        resource_id=draft.draft_id,
        payload_json={"approval_id": approval.approval_id, "draft_payload_hash": draft.payload_hash},
    )
    await db.commit()
    await db.refresh(approval)
    return ApprovalResponse(
        approval_id=approval.approval_id,
        draft_id=approval.draft_id,
        approved=approval.approved,
        approved_by=approval.approved_by,
        notes=approval.notes,
        draft_payload_hash=approval.draft_payload_hash,
        created_at=approval.created_at,
        audit_event_id=event.event_id,
    )


@router.post("/{draft_id}/approve", response_model=ApprovalResponse)
async def approve_draft(
    draft_id: str,
    request: ApprovalRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    return await _record_decision(draft_id, True, request, current_user, db)


@router.post("/{draft_id}/reject", response_model=ApprovalResponse)
async def reject_draft(
    draft_id: str,
    request: ApprovalRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    return await _record_decision(draft_id, False, request, current_user, db)
