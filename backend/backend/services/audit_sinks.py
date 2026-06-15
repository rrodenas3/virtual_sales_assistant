from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.clients.sql import DatabricksSQLClient, QueryStatement, SQLClient, param
from backend.config import settings
from backend.db.models import AuditEvent, utcnow
from backend.governance.discovery import assert_discovery_ready
from backend.services.telemetry import log_structured_event


UNITY_AUDIT_AGENT_ACTION_COLUMNS = (
    "event_id",
    "session_id",
    "rep_id",
    "territory_code",
    "event_type",
    "resource_type",
    "resource_id",
    "tool_name",
    "tool_input",
    "tool_output",
    "reasoning_trace",
    "model_id",
    "model_version",
    "requires_approval",
    "approval_status",
    "risk_level",
    "source_system",
    "data_freshness_ts",
    "created_at",
    "mlflow_run_id",
)
UNITY_AUDIT_APPROVAL_DECISION_COLUMNS = (
    "approval_id",
    "draft_id",
    "approved",
    "approved_by",
    "draft_payload_hash",
    "notes",
    "created_at",
)
_UNITY_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")


def validate_unity_table_name(table_name: str) -> str:
    if not _UNITY_TABLE_RE.fullmatch(table_name):
        raise ValueError("Unity Catalog audit table must be a three-part identifier")
    return table_name


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
    def __init__(self, client: SQLClient | None = None, table_name: str | None = None) -> None:
        self.client = client or DatabricksSQLClient(settings)
        self.table_name = validate_unity_table_name(table_name or settings.audit_unity_catalog_table)

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
            event_id=str(uuid4()),
            session_id=session_id,
            rep_id=rep_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            payload_json=payload_json,
            source_system=source_system or settings.osa_source_system,
            data_freshness_ts=data_freshness_ts,
            created_at=utcnow(),
        )
        await write_unity_catalog_event(
            self.client,
            table_name=self.table_name,
            event=event,
            payload_json=payload_json,
        )
        return event


class UnityCatalogAuditMirror:
    def __init__(self, client: SQLClient | None = None, table_name: str | None = None) -> None:
        self.client = client or DatabricksSQLClient(settings)
        self.table_name = validate_unity_table_name(table_name or settings.audit_unity_catalog_table)

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
        event = AuditEvent(
            event_id=primary_event_id,
            session_id=session_id,
            rep_id=rep_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            payload_json=payload_json,
            source_system=source_system or settings.osa_source_system,
            data_freshness_ts=data_freshness_ts,
            created_at=utcnow(),
        )
        await write_unity_catalog_event(
            self.client,
            table_name=self.table_name,
            event=event,
            payload_json=payload_json,
        )


async def write_unity_catalog_event(
    client: SQLClient,
    *,
    table_name: str,
    event: AuditEvent,
    payload_json: dict[str, Any],
) -> None:
    tool_name = str(payload_json.get("tool_name") or event.event_type)
    model_id = payload_json.get("model_id")
    requires_approval = _requires_approval(event.event_type, payload_json)
    risk_level = _risk_level(event.event_type, requires_approval)
    territory_code = payload_json.get("territory_code")
    source_system = event.source_system or settings.osa_source_system
    columns = ", ".join(UNITY_AUDIT_AGENT_ACTION_COLUMNS)
    await client.execute(
        QueryStatement(
            statement=f"""
INSERT INTO {validate_unity_table_name(table_name)} (
  {columns}
) VALUES (
  :event_id, :session_id, :rep_id, :territory_code, :event_type, :resource_type, :resource_id,
  :tool_name, parse_json(:tool_input), parse_json(:tool_output), :reasoning_trace, :model_id, :model_version,
  :requires_approval, :approval_status, :risk_level, :source_system, :data_freshness_ts,
  :created_at, :mlflow_run_id
)
""".strip(),
            parameters=(
                param("event_id", event.event_id),
                param("session_id", event.session_id),
                param("rep_id", event.rep_id),
                param("territory_code", str(territory_code or "")),
                param("event_type", event.event_type),
                param("resource_type", event.resource_type),
                param("resource_id", event.resource_id or ""),
                param("tool_name", tool_name),
                param("tool_input", json.dumps({"resource_id": event.resource_id}, sort_keys=True)),
                param("tool_output", json.dumps(payload_json, sort_keys=True, default=str)),
                param("reasoning_trace", str(payload_json.get("reasoning_trace") or "")),
                param("model_id", str(model_id or "")),
                param("model_version", str(payload_json.get("model_version") or "")),
                param("requires_approval", str(requires_approval).lower()),
                param("approval_status", str(payload_json.get("approval_status") or "")),
                param("risk_level", risk_level),
                param("source_system", source_system),
                param("data_freshness_ts", (event.data_freshness_ts or event.created_at).isoformat()),
                param("created_at", event.created_at.isoformat()),
                param("mlflow_run_id", str(payload_json.get("mlflow_run_id") or "")),
            ),
        )
    )


def _requires_approval(event_type: str, payload_json: dict[str, Any]) -> bool:
    if "requires_approval" in payload_json:
        return bool(payload_json["requires_approval"])
    return event_type in {"order_draft_created", "order_draft_approved", "order_draft_rejected", "order_submitted_sandbox"}


def _risk_level(event_type: str, requires_approval: bool) -> str:
    if event_type == "order_submitted_sandbox":
        return "high"
    if requires_approval:
        return "medium"
    return "low"


def audit_sink_status() -> dict:
    unity_selected = settings.audit_sink == "unity_catalog" or settings.audit_dual_write_enabled
    blockers: list[str] = []
    table_valid = True
    try:
        validate_unity_table_name(settings.audit_unity_catalog_table)
    except ValueError:
        table_valid = False
        blockers.append("audit_unity_catalog_table")

    if unity_selected:
        for name in ("databricks_host", "databricks_token", "databricks_sql_warehouse_id"):
            if not getattr(settings, name):
                blockers.append(name)
        if not settings.discovery_data_sharing_model:
            blockers.append("discovery_data_sharing_model")
        if not settings.discovery_data_residency:
            blockers.append("discovery_data_residency")

    return {
        "primary_sink": settings.audit_sink,
        "unity_selected": unity_selected,
        "dual_write_enabled": settings.audit_dual_write_enabled,
        "dual_write_fail_closed": settings.audit_dual_write_fail_closed,
        "unity_table": settings.audit_unity_catalog_table,
        "unity_table_valid": table_valid,
        "databricks_host_configured": bool(settings.databricks_host),
        "databricks_token_configured": bool(settings.databricks_token),
        "databricks_warehouse_configured": bool(settings.databricks_sql_warehouse_id),
        "discovery_configured": bool(settings.discovery_data_sharing_model and settings.discovery_data_residency),
        "ready": not blockers,
        "blockers": blockers,
    }


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
