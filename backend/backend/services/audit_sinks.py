from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import AuditEvent


class AuditSink(Protocol):
    async def write(
        self,
        db: AsyncSession,
        *,
        session_id: str,
        rep_id: str,
        event_type: str,
        resource_type: str,
        resource_id: str | None,
        payload_json: dict[str, Any],
        source_system: str | None,
        data_freshness_ts: datetime | None,
    ) -> AuditEvent:
        ...


class PostgresAuditSink:
    async def write(
        self,
        db: AsyncSession,
        *,
        session_id: str,
        rep_id: str,
        event_type: str,
        resource_type: str,
        resource_id: str | None,
        payload_json: dict[str, Any],
        source_system: str | None,
        data_freshness_ts: datetime | None,
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


class UnityCatalogAuditSink:
    async def write(
        self,
        db: AsyncSession,
        *,
        session_id: str,
        rep_id: str,
        event_type: str,
        resource_type: str,
        resource_id: str | None,
        payload_json: dict[str, Any],
        source_system: str | None,
        data_freshness_ts: datetime | None,
    ) -> AuditEvent:
        raise NotImplementedError("Unity Catalog audit dual-write is deferred until data governance discovery completes")


def get_audit_sink() -> AuditSink:
    if settings.audit_sink == "postgres":
        return PostgresAuditSink()
    return UnityCatalogAuditSink()
