from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.osa import OSADataPort
from backend.api.schemas import ApprovalQueueItem, ApprovalQueueResponse, TerritoryStoreSummary, TerritorySummaryResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.models import AlertFeedback, OrderDraft
from backend.db.session import get_db
from backend.deps import get_osa_adapter
from backend.governance.rbac import assert_territory_access

router = APIRouter(prefix="/manager", tags=["manager"])


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
