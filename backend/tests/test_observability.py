import json
import logging

import httpx
from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app
from backend.services import telemetry


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def test_observability_health_reports_structured_mode(monkeypatch) -> None:
    monkeypatch.setattr(settings, "observability_provider", "structured")
    monkeypatch.setattr(settings, "trace_sample_rate", 1.0)
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/health/observability")
    assert response.status_code == 200
    assert response.json()["provider"] == "structured"
    assert response.json()["trace_sample_rate"] == 1.0
    assert response.json()["otel_service_name"] == "phantom-vsa-backend"


def test_ai_health_reports_template_mode_as_not_ai_demo_ready(monkeypatch) -> None:
    monkeypatch.setattr(settings, "summary_provider", "template")
    monkeypatch.setattr(settings, "llm_model_id", "grounded-template-v1")
    monkeypatch.setattr(settings, "anthropic_token_ref", None)
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/health/ai")
    assert response.status_code == 200
    body = response.json()
    assert body["selected_provider"] == "template"
    assert body["active_model"] == "grounded-template-v1"
    assert body["ai_demo_ready"] is False
    assert "SUMMARY_PROVIDER must be anthropic for AI-demo readiness" in body["ai_demo_blockers"]


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
    assert any(
        event["request_id"] == "obs-test" and event["status_code"] == 200 and event["service_name"] == "phantom-vsa-backend"
        for event in events
    )


def test_observability_can_be_disabled(monkeypatch, caplog) -> None:
    monkeypatch.setattr(settings, "observability_provider", "none")
    monkeypatch.setattr(settings, "trace_sample_rate", 1.0)
    caplog.set_level(logging.INFO, logger="phantom.telemetry")
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert not [record for record in caplog.records if '"event_name": "http_request"' in record.message]


def test_otlp_http_exporter_emits_log_payload(monkeypatch, caplog) -> None:
    captured: dict = {}

    def fake_post(url: str, *, json: dict, timeout: float) -> httpx.Response:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return httpx.Response(200)

    monkeypatch.setattr(settings, "observability_provider", "otlp_http")
    monkeypatch.setattr(settings, "otel_exporter_otlp_endpoint", "https://otel.example")
    monkeypatch.setattr(settings, "otel_fail_closed", False)
    monkeypatch.setattr(telemetry.httpx, "post", fake_post)
    caplog.set_level(logging.INFO, logger="phantom.telemetry")

    telemetry.log_structured_event("pilot_gate", request_id="otel-test", duration_ms=12.5, status_code=200)

    assert captured["url"] == "https://otel.example/v1/logs"
    record = captured["json"]["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]
    assert record["body"]["stringValue"] == "pilot_gate"
    assert {"key": "request_id", "value": {"stringValue": "otel-test"}} in record["attributes"]
    assert any('"event_name": "pilot_gate"' in record.message for record in caplog.records)


def test_otlp_http_exporter_fails_open_without_endpoint(monkeypatch, caplog) -> None:
    monkeypatch.setattr(settings, "observability_provider", "otlp_http")
    monkeypatch.setattr(settings, "otel_exporter_otlp_endpoint", None)
    monkeypatch.setattr(settings, "otel_fail_closed", False)
    caplog.set_level(logging.INFO, logger="phantom.telemetry")

    telemetry.log_structured_event("pilot_gate", request_id="missing-endpoint")

    assert any('"event_name": "pilot_gate"' in record.message for record in caplog.records)
