from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.erp import ERPPort
from backend.adapters.osa import OSADataPort
from backend.api.schemas import CreateOrderDraftRequest, OrderDraftResponse, SandboxSubmitResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.models import ApprovalRecord, OrderDraft
from backend.db.session import get_db
from backend.deps import get_erp_adapter, get_osa_adapter
from backend.governance.rbac import assert_store_access
from backend.services.audit import log_audit_event
from backend.services.agent_actions import AgentActionNotFound, create_order_draft_action, order_draft_response

router = APIRouter(prefix="/orders", tags=["orders"])


def _draft_response(draft: OrderDraft, audit_event_id: str | None = None) -> OrderDraftResponse:
    return order_draft_response(draft, audit_event_id)


def _http_error_for_action(exc: ValueError) -> HTTPException:
    if isinstance(exc, AgentActionNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/drafts", response_model=OrderDraftResponse)
async def create_order_draft(
    request: CreateOrderDraftRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> OrderDraftResponse:
    try:
        return await create_order_draft_action(db, osa, current_user, request)
    except ValueError as exc:
        raise _http_error_for_action(exc) from exc


@router.get("/drafts/{draft_id}", response_model=OrderDraftResponse)
async def get_order_draft(
    draft_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderDraftResponse:
    draft = await db.get(OrderDraft, draft_id)
    if not draft or (current_user.role != "admin" and draft.rep_id != current_user.rep_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    return _draft_response(draft)


@router.post("/drafts/{draft_id}/submit-sandbox", response_model=SandboxSubmitResponse)
async def submit_order_draft_sandbox(
    draft_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    erp: ERPPort = Depends(get_erp_adapter),
) -> SandboxSubmitResponse:
    draft = await db.get(OrderDraft, draft_id)
    if not draft or (current_user.role != "admin" and draft.rep_id != current_user.rep_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    if draft.status != "APPROVED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Draft must be approved before submit")

    approval = (
        await db.execute(
            select(ApprovalRecord)
            .where(ApprovalRecord.draft_id == draft.draft_id)
            .where(ApprovalRecord.approved.is_(True))
            .where(ApprovalRecord.draft_payload_hash == draft.payload_hash)
            .order_by(ApprovalRecord.created_at.desc())
        )
    ).scalars().first()
    if not approval:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Matching approval not found")

    submit_result = await erp.submit_order(draft.draft_id, draft.payload_json, approval.approval_id, draft.payload_hash)
    draft.status = "SUBMITTED_SANDBOX"
    event = await log_audit_event(
        db,
        session_id=draft.session_id,
        rep_id=current_user.rep_id,
        event_type="order_sandbox_submitted",
        resource_type="order_draft",
        resource_id=draft.draft_id,
        payload_json={
            "erp_order_id": submit_result.erp_order_id,
            "approval_id": approval.approval_id,
            "payload_hash": draft.payload_hash,
            "submit_status": submit_result.status,
        },
    )
    await db.commit()
    return SandboxSubmitResponse(
        draft_id=draft.draft_id,
        status=draft.status,
        erp_order_id=submit_result.erp_order_id,
        submitted_at=event.created_at,
        approval_id=approval.approval_id,
        payload_hash=draft.payload_hash,
        audit_event_id=event.event_id,
    )


async def get_draft_for_approval(
    db: AsyncSession,
    draft_id: str,
    current_user: CurrentUser,
    osa: OSADataPort | None = None,
) -> OrderDraft:
    draft = (await db.execute(select(OrderDraft).where(OrderDraft.draft_id == draft_id))).scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    if current_user.role == "admin" or draft.rep_id == current_user.rep_id:
        pass
    elif current_user.role == "manager" and osa is not None:
        try:
            store = await osa.get_store_detail_any(draft.store_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found") from exc
        assert_store_access(current_user, store.rep_id, store.territory_code)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    if draft.status not in {"DRAFT", "REJECTED"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Draft is no longer approvable")
    return draft
