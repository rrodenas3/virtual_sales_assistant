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
    UpdateManagerTaskStatusRequest,
)
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.models import AlertFeedback, ManagerTask, OrderDraft
from backend.db.session import get_db
from backend.deps import get_osa_adapter
from backend.governance.rbac import assert_territory_access
from backend.services.audit import log_audit_event
from backend.services.agent_actions import (
    AgentActionConflict,
    AgentActionForbidden,
    AgentActionNotFound,
    create_manager_task_action,
    manager_task_response,
)
from backend.services.manager_tasks import manager_task_status_payload

router = APIRouter(prefix="/manager", tags=["manager"])


def _task_response(row: ManagerTask, store_name: str | None = None, audit_event_id: str | None = None) -> ManagerTaskResponse:
    return manager_task_response(row, store_name, audit_event_id)


def _http_error_for_action(exc: ValueError) -> HTTPException:
    if isinstance(exc, AgentActionForbidden):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, AgentActionNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, AgentActionConflict):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


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
    try:
        return await create_manager_task_action(db, osa, current_user, request)
    except ValueError as exc:
        raise _http_error_for_action(exc) from exc


@router.get("/tasks", response_model=ManagerTaskListResponse)
async def manager_tasks(
    territory_code: str,
    task_status: str | None = Query(default=None, alias="status", pattern="^(OPEN|COMPLETED|BLOCKED|CANCELLED)$"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> ManagerTaskListResponse:
    if current_user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager role required")
    assert_territory_access(current_user, territory_code)
    statement = select(ManagerTask).where(ManagerTask.territory_code == territory_code)
    if task_status is not None:
        statement = statement.where(ManagerTask.status == task_status)
    rows = list(
        (
            await db.execute(
                statement.order_by(ManagerTask.created_at.desc())
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
    task_status: str | None = Query(default=None, alias="status", pattern="^(OPEN|COMPLETED|BLOCKED|CANCELLED)$"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> ManagerTaskListResponse:
    if current_user.role != "rep":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rep role required")
    statement = select(ManagerTask).where(ManagerTask.assigned_rep_id == current_user.rep_id)
    if task_status is not None:
        statement = statement.where(ManagerTask.status == task_status)
    rows = list(
        (
            await db.execute(
                statement.order_by(ManagerTask.created_at.desc())
            )
        ).scalars()
    )
    summaries = await osa.get_territory_store_summaries(current_user.territory_code or "", date.today())
    stores_by_id = {store.store_id: store.store_name for store in summaries}
    return ManagerTaskListResponse(
        assigned_rep_id=current_user.rep_id,
        tasks=[_task_response(row, stores_by_id.get(row.store_id)) for row in rows],
    )


@router.post("/tasks/{task_id}/status", response_model=ManagerTaskResponse)
async def update_manager_task_status(
    task_id: str,
    request: UpdateManagerTaskStatusRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> ManagerTaskResponse:
    row = (
        await db.execute(
            select(ManagerTask)
            .where(ManagerTask.task_id == task_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    try:
        store = await osa.get_store_detail_any(row.store_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found") from exc

    if current_user.role == "rep":
        if row.assigned_rep_id != current_user.rep_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        if request.status not in {"COMPLETED", "BLOCKED"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rep cannot cancel manager tasks")
    elif current_user.role in {"manager", "admin"}:
        assert_territory_access(current_user, row.territory_code)
        if request.status != "CANCELLED":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager can only cancel tasks")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unsupported role")

    previous_status = row.status
    row.status = request.status
    row.payload_json = manager_task_status_payload(
        row.payload_json,
        notes=request.notes,
        updated_by=current_user.rep_id,
        previous_status=previous_status,
    )

    event = await log_audit_event(
        db,
        session_id=request.session_id,
        rep_id=current_user.rep_id,
        event_type="manager_task_status_updated",
        resource_type="manager_task",
        resource_id=row.task_id,
        payload_json={
            "task_id": row.task_id,
            "previous_status": previous_status,
            "status": row.status,
            "assigned_rep_id": row.assigned_rep_id,
            "store_id": row.store_id,
            "notes": request.notes,
        },
        data_freshness_ts=store.data_freshness_ts,
    )
    await db.commit()
    return _task_response(row, store.store_name, event.event_id)
