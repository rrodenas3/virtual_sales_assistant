from fastapi.testclient import TestClient

from backend.config import settings
from backend.governance.discovery import readiness_blockers, selected_live_modes
from backend.main import app
from backend.services.audit_sinks import CompositeAuditSink, PostgresAuditSink, get_audit_sink


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
