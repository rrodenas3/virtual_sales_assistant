from fastapi.testclient import TestClient
import pytest

from backend.clients.sql import QueryStatement
from backend.config import settings
from backend.governance.discovery import readiness_blockers, selected_live_modes
from backend.main import app
from backend.services.audit_sinks import CompositeAuditSink, PostgresAuditSink, UnityCatalogAuditMirror, get_audit_sink


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
