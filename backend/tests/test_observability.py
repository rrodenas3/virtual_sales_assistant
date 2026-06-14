import json
import logging

from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def test_observability_health_reports_structured_mode(monkeypatch) -> None:
    monkeypatch.setattr(settings, "observability_provider", "structured")
    monkeypatch.setattr(settings, "trace_sample_rate", 1.0)
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/health/observability")
    assert response.status_code == 200
    assert response.json()["provider"] == "structured"
    assert response.json()["trace_sample_rate"] == 1.0


def test_request_middleware_logs_structured_http_event(monkeypatch, caplog) -> None:
    monkeypatch.setattr(settings, "observability_provider", "structured")
    monkeypatch.setattr(settings, "trace_sample_rate", 1.0)
    caplog.set_level(logging.INFO, logger="phantom.telemetry")
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}", "x-request-id": "obs-test"}) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "obs-test"
    assert float(response.headers["x-response-time-ms"]) >= 0
    events = [json.loads(record.message) for record in caplog.records if '"event_name": "http_request"' in record.message]
    assert any(event["request_id"] == "obs-test" and event["status_code"] == 200 for event in events)


def test_observability_can_be_disabled(monkeypatch, caplog) -> None:
    monkeypatch.setattr(settings, "observability_provider", "none")
    monkeypatch.setattr(settings, "trace_sample_rate", 1.0)
    caplog.set_level(logging.INFO, logger="phantom.telemetry")
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert not [record for record in caplog.records if '"event_name": "http_request"' in record.message]
