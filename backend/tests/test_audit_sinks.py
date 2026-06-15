from fastapi.testclient import TestClient
from pathlib import Path
import pytest

from backend.clients.sql import QueryStatement
from backend.config import settings
from backend.governance.discovery import readiness_blockers, selected_live_modes
from backend.main import app
from backend.services.audit_sinks import (
    CompositeAuditSink,
    PostgresAuditSink,
    UNITY_AUDIT_AGENT_ACTION_COLUMNS,
    UNITY_AUDIT_APPROVAL_DECISION_COLUMNS,
    UnityCatalogAuditMirror,
    get_audit_sink,
    validate_unity_table_name,
)


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def authorized_client() -> TestClient:
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {REP_001}"})
    return c


def test_default_audit_sink_is_postgres(monkeypatch) -> None:
    monkeypatch.setattr(settings, "audit_sink", "postgres")
    monkeypatch.setattr(settings, "audit_dual_write_enabled", False)
    assert isinstance(get_audit_sink(), PostgresAuditSink)


def test_audit_dual_write_is_a_unity_catalog_live_mode(monkeypatch) -> None:
    monkeypatch.setattr(settings, "audit_sink", "postgres")
    monkeypatch.setattr(settings, "audit_dual_write_enabled", True)
    monkeypatch.setattr(settings, "discovery_data_sharing_model", None)
    monkeypatch.setattr(settings, "discovery_data_residency", None)

    assert "unity_catalog" in selected_live_modes()
    assert "discovery_data_sharing_model" in readiness_blockers()
    assert "discovery_data_residency" in readiness_blockers()


def test_unity_catalog_table_name_rejects_non_identifier_sql() -> None:
    assert validate_unity_table_name("phantom.audit.agent_actions") == "phantom.audit.agent_actions"
    with pytest.raises(ValueError, match="three-part identifier"):
        validate_unity_table_name("phantom.audit.agent_actions;drop")


def test_dual_write_fail_open_keeps_primary_postgres_audit(monkeypatch) -> None:
    monkeypatch.setattr(settings, "audit_sink", "postgres")
    monkeypatch.setattr(settings, "audit_dual_write_enabled", True)
    monkeypatch.setattr(settings, "audit_dual_write_fail_closed", False)
    monkeypatch.setattr(settings, "discovery_data_sharing_model", "client_databricks")
    monkeypatch.setattr(settings, "discovery_data_residency", "eu-west")
    assert isinstance(get_audit_sink(), CompositeAuditSink)

    with authorized_client() as c:
        response = c.get("/api/v1/stores/ST-001")
        assert response.status_code == 200
        audit_event_id = response.json()["audit_event_id"]

        audit = c.get("/api/v1/audit/session/REP-001:store:ST-001")
        assert audit.status_code == 200
        assert any(event["event_id"] == audit_event_id for event in audit.json()["events"])


class FakeSQLClient:
    def __init__(self) -> None:
        self.queries: list[QueryStatement] = []

    async def execute(self, query: QueryStatement) -> list[dict]:
        self.queries.append(query)
        return []


@pytest.mark.asyncio
async def test_unity_catalog_mirror_writes_parameterized_insert() -> None:
    client = FakeSQLClient()
    mirror = UnityCatalogAuditMirror(client=client, table_name="phantom.audit.agent_actions")

    await mirror.write_mirror(
        primary_event_id="audit-1",
        session_id="session-1",
        rep_id="REP-001",
        event_type="osa_summary_created",
        resource_type="agent_summary",
        resource_id="ST-001",
        payload_json={"model_id": "grounded-template-v1", "territory_code": "WEST-01"},
        source_system="mock",
        data_freshness_ts=None,
    )

    query = client.queries[0]
    assert "INSERT INTO phantom.audit.agent_actions" in query.statement
    assert "REP-001" not in query.statement
    assert "event_id, session_id, rep_id" in query.statement
    params = {param.name: param.value for param in query.parameters}
    assert params["event_id"] == "audit-1"
    assert params["rep_id"] == "REP-001"
    assert params["territory_code"] == "WEST-01"
    assert params["requires_approval"] == "false"


@pytest.mark.asyncio
async def test_unity_catalog_mirror_marks_order_submit_as_high_risk() -> None:
    client = FakeSQLClient()
    mirror = UnityCatalogAuditMirror(client=client, table_name="phantom.audit.agent_actions")

    await mirror.write_mirror(
        primary_event_id="audit-2",
        session_id="session-2",
        rep_id="REP-001",
        event_type="order_submitted_sandbox",
        resource_type="order_draft",
        resource_id="draft-1",
        payload_json={},
        source_system="mock",
        data_freshness_ts=None,
    )

    params = {param.name: param.value for param in client.queries[0].parameters}
    assert params["requires_approval"] == "true"
    assert params["risk_level"] == "high"


def test_unity_catalog_ddl_matches_runtime_contract() -> None:
    ddl = (Path(__file__).resolve().parents[2] / "infra" / "databricks" / "audit_table_ddl.sql").read_text(encoding="utf-8")

    agent_columns = _ddl_columns(ddl, "phantom.audit.agent_actions")
    approval_columns = _ddl_columns(ddl, "phantom.audit.approval_decisions")

    assert agent_columns == list(UNITY_AUDIT_AGENT_ACTION_COLUMNS)
    assert approval_columns == list(UNITY_AUDIT_APPROVAL_DECISION_COLUMNS)
    assert "delta.appendOnly = true" in ddl
    executable = "\n".join(line for line in ddl.upper().splitlines() if not line.strip().startswith("--"))
    assert "UPDATE " not in executable
    assert "DELETE " not in executable


def _ddl_columns(ddl: str, table_name: str) -> list[str]:
    start = ddl.index(f"CREATE TABLE IF NOT EXISTS {table_name} (")
    body = ddl[start:].split(")", 1)[0].split("(", 1)[1]
    columns = []
    for line in body.splitlines():
        stripped = line.strip().rstrip(",")
        if not stripped:
            continue
        columns.append(stripped.split()[0])
    return columns
