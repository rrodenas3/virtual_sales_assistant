from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import AlertFeedback, AuditEvent


async def log_audit_event(
    db: AsyncSession,
    *,
    session_id: str,
    rep_id: str,
    event_type: str,
    resource_type: str,
    resource_id: str | None,
    payload_json: dict[str, Any],
    source_system: str | None = None,
    data_freshness_ts: datetime | None = None,
) -> AuditEvent:
    event = AuditEvent(
        session_id=session_id,
        rep_id=rep_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        payload_json=payload_json,
        source_system=source_system or settings.osa_source_system,
        data_freshness_ts=data_freshness_ts,
    )
    db.add(event)
    await db.flush()
    return event


async def get_session_audit(db: AsyncSession, session_id: str) -> tuple[list[AuditEvent], list[AlertFeedback]]:
    events = list((await db.execute(select(AuditEvent).where(AuditEvent.session_id == session_id))).scalars())
    feedback = list((await db.execute(select(AlertFeedback).where(AlertFeedback.session_id == session_id))).scalars())
    return events, feedback

