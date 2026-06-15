from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import AuditEvent
from backend.governance.discovery import assert_discovery_ready
from backend.services.telemetry import log_structured_event


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


class UnityCatalogAuditMirror:
    async def write_mirror(
        self,
        *,
        primary_event_id: str,
        session_id: str,
        rep_id: str,
        event_type: str,
        resource_type: str,
        resource_id: str | None,
        payload_json: dict[str, Any],
        source_system: str | None,
        data_freshness_ts: datetime | None,
    ) -> None:
        raise NotImplementedError("Unity Catalog audit mirror is deferred until data governance discovery completes")


class CompositeAuditSink:
    def __init__(
        self,
        primary: AuditSink,
        mirrors: list[UnityCatalogAuditMirror],
        *,
        fail_closed: bool,
    ) -> None:
        self.primary = primary
        self.mirrors = mirrors
        self.fail_closed = fail_closed

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
        event = await self.primary.write(
            db,
            session_id=session_id,
            rep_id=rep_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            payload_json=payload_json,
            source_system=source_system,
            data_freshness_ts=data_freshness_ts,
        )
        for mirror in self.mirrors:
            try:
                await mirror.write_mirror(
                    primary_event_id=event.event_id,
                    session_id=session_id,
                    rep_id=rep_id,
                    event_type=event_type,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    payload_json=payload_json,
                    source_system=source_system or settings.osa_source_system,
                    data_freshness_ts=data_freshness_ts,
                )
            except Exception as exc:  # noqa: BLE001
                log_structured_event(
                    "audit_mirror_failed",
                    primary_event_id=event.event_id,
                    mirror_type=type(mirror).__name__,
                    fail_closed=self.fail_closed,
                    error_type=type(exc).__name__,
                    event_type=event_type,
                    resource_type=resource_type,
                )
                if self.fail_closed:
                    raise
        return event


def get_audit_sink() -> AuditSink:
    if settings.audit_sink == "postgres":
        primary = PostgresAuditSink()
        if settings.audit_dual_write_enabled:
            assert_discovery_ready("unity_catalog")
            return CompositeAuditSink(
                primary,
                [UnityCatalogAuditMirror()],
                fail_closed=settings.audit_dual_write_fail_closed,
            )
        return primary
    assert_discovery_ready("unity_catalog")
    return UnityCatalogAuditSink()
