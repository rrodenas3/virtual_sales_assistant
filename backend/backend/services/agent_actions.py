from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.crm import CRMPort
from backend.adapters.osa import OSADataPort
from backend.api.schemas import (
    CreateManagerTaskRequest,
    CreateOrderDraftRequest,
    ManagerTaskResponse,
    OrderDraftResponse,
    VisitLogDraftRequest,
    VisitLogDraftResponse,
)
from backend.auth.mock_jwt import CurrentUser
from backend.db.models import ManagerTask, OrderDraft, VisitLog
from backend.governance.rbac import assert_store_access, assert_territory_access
from backend.services.audit import log_audit_event
from backend.services.hashing import stable_payload_hash
from backend.services.manager_tasks import manager_task_payload


class AgentActionError(ValueError):
    pass


class AgentActionForbidden(AgentActionError):
    pass


class AgentActionNotFound(AgentActionError):
    pass


class AgentActionConflict(AgentActionError):
    pass


def order_draft_response(draft: OrderDraft, audit_event_id: str | None = None) -> OrderDraftResponse:
    return OrderDraftResponse(
        draft_id=draft.draft_id,
        store_id=draft.store_id,
        rep_id=draft.rep_id,
        session_id=draft.session_id,
        payload_json=draft.payload_json,
        payload_hash=draft.payload_hash,
        status=draft.status,
        created_at=draft.created_at,
        audit_event_id=audit_event_id,
    )


def manager_task_response(
    row: ManagerTask,
    store_name: str | None = None,
    audit_event_id: str | None = None,
) -> ManagerTaskResponse:
    return ManagerTaskResponse(
        task_id=row.task_id,
        territory_code=row.territory_code,
        store_id=row.store_id,
        store_name=store_name,
        assigned_rep_id=row.assigned_rep_id,
        created_by=row.created_by,
        session_id=row.session_id,
        title=row.title,
        task_type=row.task_type,
        priority=row.priority,
        due_date=row.due_date,
        status=row.status,
        payload_json=row.payload_json,
        created_at=row.created_at,
        audit_event_id=audit_event_id,
    )


async def create_order_draft_action(
    db: AsyncSession,
    osa: OSADataPort,
    current_user: CurrentUser,
    request: CreateOrderDraftRequest,
) -> OrderDraftResponse:
    try:
        store = await osa.get_store_detail(current_user.rep_id, request.store_id)
    except KeyError as exc:
        raise AgentActionNotFound("Store not found") from exc
    assert_store_access(current_user, store.rep_id, store.territory_code)

    payload = {
        "store_id": request.store_id,
        "rep_id": current_user.rep_id,
        "items": [item.model_dump() for item in request.items],
        "notes": request.notes,
    }
    draft = OrderDraft(
        store_id=request.store_id,
        rep_id=current_user.rep_id,
        session_id=request.session_id,
        payload_json=payload,
        payload_hash=stable_payload_hash(payload),
        status="DRAFT",
    )
    db.add(draft)
    await db.flush()
    event = await log_audit_event(
        db,
        session_id=request.session_id,
        rep_id=current_user.rep_id,
        event_type="order_draft_created",
        resource_type="order_draft",
        resource_id=draft.draft_id,
        payload_json={"payload_hash": draft.payload_hash, "item_count": len(request.items)},
        data_freshness_ts=store.data_freshness_ts,
    )
    await db.commit()
    await db.refresh(draft)
    return order_draft_response(draft, event.event_id)


async def create_visit_log_draft_action(
    db: AsyncSession,
    osa: OSADataPort,
    crm: CRMPort,
    current_user: CurrentUser,
    request: VisitLogDraftRequest,
) -> VisitLogDraftResponse:
    try:
        store = await osa.get_store_detail(current_user.rep_id, request.store_id)
    except KeyError as exc:
        raise AgentActionNotFound("Store not found") from exc
    assert_store_access(current_user, store.rep_id, store.territory_code)
    payload = {
        "store_id": request.store_id,
        "rep_id": current_user.rep_id,
        "session_id": request.session_id,
        "notes": request.notes,
        "outcome": request.outcome,
    }
    submit_result = await crm.submit_visit_log(payload)
    draft = VisitLog(
        store_id=request.store_id,
        rep_id=current_user.rep_id,
        session_id=request.session_id,
        payload_json=payload,
        status=submit_result.status,
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
        payload_json={
            "status": draft.status,
            "outcome": request.outcome,
            "external_id": submit_result.external_id,
        },
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


async def create_manager_task_action(
    db: AsyncSession,
    osa: OSADataPort,
    current_user: CurrentUser,
    request: CreateManagerTaskRequest,
) -> ManagerTaskResponse:
    if current_user.role not in {"manager", "admin"}:
        raise AgentActionForbidden("Manager role required")
    assert_territory_access(current_user, request.territory_code)
    try:
        store = await osa.get_store_detail_any(request.store_id)
    except KeyError as exc:
        raise AgentActionNotFound("Store not found") from exc
    if store.territory_code != request.territory_code:
        raise AgentActionNotFound("Store not found")
    if store.rep_id != request.assigned_rep_id:
        raise AgentActionError("assigned_rep_id does not match store owner")

    existing_open_task = (
        await db.execute(
            select(ManagerTask)
            .where(ManagerTask.territory_code == request.territory_code)
            .where(ManagerTask.store_id == request.store_id)
            .where(ManagerTask.assigned_rep_id == request.assigned_rep_id)
            .where(ManagerTask.task_type == request.task_type)
            .where(ManagerTask.title == request.title)
            .where(ManagerTask.status == "OPEN")
            .order_by(ManagerTask.created_at.desc())
        )
    ).scalars().first()
    if existing_open_task is not None:
        return manager_task_response(existing_open_task, store.store_name)

    row = ManagerTask(
        territory_code=request.territory_code,
        store_id=request.store_id,
        assigned_rep_id=request.assigned_rep_id,
        created_by=current_user.rep_id,
        session_id=request.session_id,
        title=request.title,
        task_type=request.task_type,
        priority=request.priority,
        due_date=request.due_date,
        payload_json=manager_task_payload(notes=request.notes, linked_alert_ids=request.linked_alert_ids),
        status="OPEN",
    )
    db.add(row)
    await db.flush()
    event = await log_audit_event(
        db,
        session_id=request.session_id,
        rep_id=current_user.rep_id,
        event_type="manager_task_created",
        resource_type="manager_task",
        resource_id=row.task_id,
        payload_json={
            "task_id": row.task_id,
            "territory_code": row.territory_code,
            "store_id": row.store_id,
            "assigned_rep_id": row.assigned_rep_id,
            "task_type": row.task_type,
            "priority": row.priority,
            "linked_alert_ids": request.linked_alert_ids,
        },
        data_freshness_ts=store.data_freshness_ts,
    )
    await db.commit()
    return manager_task_response(row, store.store_name, event.event_id)
