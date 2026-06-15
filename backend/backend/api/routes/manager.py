from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.osa import OSADataPort
from backend.api.schemas import (
    ApprovalQueueItem,
    ApprovalQueueResponse,
    CreateManagerTaskRequest,
    ManagerTaskListResponse,
    ManagerTaskResponse,
    TerritoryStoreSummary,
    TerritorySummaryResponse,
)
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.models import AlertFeedback, ManagerTask, OrderDraft
from backend.db.session import get_db
from backend.deps import get_osa_adapter
from backend.governance.rbac import assert_territory_access
from backend.services.audit import log_audit_event

router = APIRouter(prefix="/manager", tags=["manager"])


def _task_response(row: ManagerTask, store_name: str | None = None, audit_event_id: str | None = None) -> ManagerTaskResponse:
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


@router.get("/territory-summary", response_model=TerritorySummaryResponse)
async def territory_summary(
    territory_code: str,
    visit_date: date | None = Query(default=None, alias="date"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> TerritorySummaryResponse:
    if current_user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager role required")
    assert_territory_access(current_user, territory_code)
    summaries = await osa.get_territory_store_summaries(territory_code, visit_date or date.today())

    feedback_rows = list((await db.execute(select(AlertFeedback))).scalars())
    draft_rows = list((await db.execute(select(OrderDraft))).scalars())

    enriched: list[TerritoryStoreSummary] = []
    for store in summaries:
        store_feedback = [row for row in feedback_rows if row.store_id == store.store_id]
        open_drafts = [
            row
            for row in draft_rows
            if row.store_id == store.store_id and row.status in {"DRAFT", "APPROVED", "REJECTED"}
        ]
        enriched.append(
            store.model_copy(
                update={
                    "confirmed_feedback_count": len([row for row in store_feedback if row.feedback == "confirmed"]),
                    "false_positive_count": len([row for row in store_feedback if row.feedback == "false_positive"]),
                    "open_draft_count": len(open_drafts),
                }
            )
        )

    return TerritorySummaryResponse(
        territory_code=territory_code,
        store_count=len(enriched),
        total_oos_alerts=sum(row.oos_sku_count for row in enriched),
        confirmed_feedback_count=sum(row.confirmed_feedback_count for row in enriched),
        false_positive_count=sum(row.false_positive_count for row in enriched),
        open_draft_count=sum(row.open_draft_count for row in enriched),
        stores=enriched,
    )


@router.get("/approval-queue", response_model=ApprovalQueueResponse)
async def approval_queue(
    territory_code: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> ApprovalQueueResponse:
    if current_user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager role required")
    assert_territory_access(current_user, territory_code)
    summaries = await osa.get_territory_store_summaries(territory_code, date.today())
    stores_by_id = {store.store_id: store for store in summaries}
    rows = list(
        (
            await db.execute(
                select(OrderDraft)
                .where(OrderDraft.store_id.in_(list(stores_by_id)))
                .where(OrderDraft.status.in_(["DRAFT", "REJECTED"]))
                .order_by(OrderDraft.created_at.desc())
            )
        ).scalars()
    )
    items: list[ApprovalQueueItem] = []
    for row in rows:
        store = stores_by_id[row.store_id]
        items.append(
            ApprovalQueueItem(
                draft_id=row.draft_id,
                store_id=row.store_id,
                store_name=store.store_name,
                rep_id=row.rep_id,
                session_id=row.session_id,
                status=row.status,
                payload_hash=row.payload_hash,
                item_count=len(row.payload_json.get("items", [])),
                notes=row.payload_json.get("notes"),
                created_at=row.created_at,
            )
        )
    return ApprovalQueueResponse(territory_code=territory_code, pending_count=len(items), items=items)


@router.post("/tasks", response_model=ManagerTaskResponse)
async def create_manager_task(
    request: CreateManagerTaskRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> ManagerTaskResponse:
    if current_user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager role required")
    assert_territory_access(current_user, request.territory_code)
    try:
        store = await osa.get_store_detail_any(request.store_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found") from exc
    if store.territory_code != request.territory_code:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    if store.rep_id != request.assigned_rep_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assigned_rep_id does not match store owner")

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
        payload_json={"notes": request.notes, "linked_alert_ids": request.linked_alert_ids},
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
    return _task_response(row, store.store_name, event.event_id)


@router.get("/tasks", response_model=ManagerTaskListResponse)
async def manager_tasks(
    territory_code: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> ManagerTaskListResponse:
    if current_user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager role required")
    assert_territory_access(current_user, territory_code)
    rows = list(
        (
            await db.execute(
                select(ManagerTask)
                .where(ManagerTask.territory_code == territory_code)
                .order_by(ManagerTask.created_at.desc())
            )
        ).scalars()
    )
    summaries = await osa.get_territory_store_summaries(territory_code, date.today())
    stores_by_id = {store.store_id: store.store_name for store in summaries}
    return ManagerTaskListResponse(
        territory_code=territory_code,
        tasks=[_task_response(row, stores_by_id.get(row.store_id)) for row in rows],
    )


@router.get("/my-tasks", response_model=ManagerTaskListResponse)
async def my_manager_tasks(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> ManagerTaskListResponse:
    if current_user.role != "rep":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rep role required")
    rows = list(
        (
            await db.execute(
                select(ManagerTask)
                .where(ManagerTask.assigned_rep_id == current_user.rep_id)
                .order_by(ManagerTask.created_at.desc())
            )
        ).scalars()
    )
    summaries = await osa.get_territory_store_summaries(current_user.territory_code or "", date.today())
    stores_by_id = {store.store_id: store.store_name for store in summaries}
    return ManagerTaskListResponse(
        assigned_rep_id=current_user.rep_id,
        tasks=[_task_response(row, stores_by_id.get(row.store_id)) for row in rows],
    )
