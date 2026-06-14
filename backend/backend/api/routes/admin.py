from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import AdminAuditEventDetailResponse, AdminAuditEventsResponse, AuditEventOut
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.models import AuditEvent
from backend.db.session import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


def _audit_out(row: AuditEvent) -> AuditEventOut:
    return AuditEventOut(
        event_id=row.event_id,
        session_id=row.session_id,
        rep_id=row.rep_id,
        event_type=row.event_type,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        payload_json=row.payload_json,
        source_system=row.source_system,
        data_freshness_ts=row.data_freshness_ts,
        created_at=row.created_at,
    )


@router.get("/audit-events", response_model=AdminAuditEventsResponse)
async def audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    cursor: str | None = None,
    event_type: str | None = None,
    rep_id: str | None = None,
    resource_type: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdminAuditEventsResponse:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    offset = int(cursor or "0")
    query = select(AuditEvent)
    if event_type:
        query = query.where(AuditEvent.event_type == event_type)
    if rep_id:
        query = query.where(AuditEvent.rep_id == rep_id)
    if resource_type:
        query = query.where(AuditEvent.resource_type == resource_type)
    rows = list(
        (
            await db.execute(
                query.order_by(AuditEvent.created_at.desc(), AuditEvent.event_id.desc()).offset(offset).limit(limit + 1)
            )
        ).scalars()
    )
    page_rows = rows[:limit]
    next_cursor = str(offset + limit) if len(rows) > limit else None
    return AdminAuditEventsResponse(
        limit=limit,
        next_cursor=next_cursor,
        events=[_audit_out(row) for row in page_rows],
    )


@router.get("/audit-events/{event_id}", response_model=AdminAuditEventDetailResponse)
async def audit_event_detail(
    event_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdminAuditEventDetailResponse:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    row = await db.get(AuditEvent, event_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit event not found")
    return AdminAuditEventDetailResponse(event=_audit_out(row))
