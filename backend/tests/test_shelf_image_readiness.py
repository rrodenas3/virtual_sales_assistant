from fastapi.testclient import TestClient

from backend.config import settings
from backend.governance.shelf_image import shelf_image_status
from backend.main import app


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."


def test_shelf_image_status_reports_mock_default_ready(monkeypatch) -> None:
    monkeypatch.setattr(settings, "shelf_image_adapter", "mock")
    monkeypatch.setattr(settings, "shelf_image_endpoint", None)
    monkeypatch.setattr(settings, "shelf_image_token_ref", None)
    monkeypatch.setattr(settings, "discovery_data_residency", None)

    status = shelf_image_status()

    assert status["provider"] == "mock"
    assert status["ready"] is True
    assert status["blockers"] == []


def test_shelf_image_status_reports_external_blockers(monkeypatch) -> None:
    monkeypatch.setattr(settings, "shelf_image_adapter", "external")
    monkeypatch.setattr(settings, "shelf_image_endpoint", None)
    monkeypatch.setattr(settings, "shelf_image_token_ref", None)
    monkeypatch.setattr(settings, "discovery_rep_device", None)
    monkeypatch.setattr(settings, "discovery_data_residency", None)

    status = shelf_image_status()

    assert status["external_enabled"] is True
    assert status["ready"] is False
    assert status["blockers"] == [
        "shelf_image_endpoint",
        "shelf_image_token_ref",
        "discovery_rep_device",
        "discovery_data_residency",
    ]


def test_shelf_image_status_reports_external_ready(monkeypatch) -> None:
    monkeypatch.setattr(settings, "shelf_image_adapter", "external")
    monkeypatch.setattr(settings, "shelf_image_endpoint", "https://vision.example.test")
    monkeypatch.setattr(settings, "shelf_image_token_ref", "approved-token-reference")
    monkeypatch.setattr(settings, "discovery_rep_device", "approved-pwa")
    monkeypatch.setattr(settings, "discovery_data_residency", "approved-region")

    status = shelf_image_status()

    assert status["ready"] is True
    assert status["endpoint_configured"] is True
    assert status["token_ref_configured"] is True
    assert status["blockers"] == []


def test_shelf_image_health_endpoint_reports_selected_provider(monkeypatch) -> None:
    monkeypatch.setattr(settings, "shelf_image_adapter", "external")
    monkeypatch.setattr(settings, "shelf_image_endpoint", "https://vision.example.test")
    monkeypatch.setattr(settings, "shelf_image_token_ref", None)
    monkeypatch.setattr(settings, "discovery_rep_device", "approved-pwa")
    monkeypatch.setattr(settings, "discovery_data_residency", "approved-region")

    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/health/shelf-image")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "external"
    assert body["ready"] is False
    assert body["blockers"] == ["shelf_image_token_ref"]
