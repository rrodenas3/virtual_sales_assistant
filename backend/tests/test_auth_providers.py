from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app


REP_001 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."
BAD_ROLE = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6Im93bmVyIn0."


def test_missing_token_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/visits/today?territory_code=WEST-01")
    assert response.status_code == 401


def test_invalid_role_is_rejected() -> None:
    with TestClient(app, headers={"Authorization": f"Bearer {BAD_ROLE}"}) as client:
        response = client.get("/api/v1/visits/today?territory_code=WEST-01")
    assert response.status_code == 401


def test_external_jwt_provider_fails_closed_when_unconfigured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_provider", "external_jwt")
    monkeypatch.setattr(settings, "external_jwt_issuer", None)
    monkeypatch.setattr(settings, "external_jwt_audience", None)
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/visits/today?territory_code=WEST-01")
    assert response.status_code == 503


def test_mock_provider_still_authenticates(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_provider", "mock")
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/visits/today?territory_code=WEST-01")
    assert response.status_code == 200
