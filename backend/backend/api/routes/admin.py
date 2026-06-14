from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import AdminAuditEventsResponse, AuditEventOut
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.db.models import AuditEvent
from backend.db.session import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-events", response_model=AdminAuditEventsResponse)
async def audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdminAuditEventsResponse:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    rows = list(
        (
            await db.execute(
                select(AuditEvent)
                .order_by(AuditEvent.created_at.desc())
                .limit(limit)
            )
        ).scalars()
    )
    return AdminAuditEventsResponse(
        limit=limit,
        events=[
            AuditEventOut(
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
            for row in rows
        ],
    )

