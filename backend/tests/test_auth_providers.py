from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt
from jose.utils import base64url_encode

from backend.config import settings
from backend.main import app
from backend.auth import providers
from backend.auth.providers import auth_status


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
    monkeypatch.setattr(settings, "discovery_sso_provider", "Azure AD")
    monkeypatch.setattr(settings, "external_jwt_issuer", None)
    monkeypatch.setattr(settings, "external_jwt_audience", None)
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/visits/today?territory_code=WEST-01")
    assert response.status_code == 503


def test_auth_status_reports_mock_default_ready(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_provider", "mock")
    monkeypatch.setattr(settings, "discovery_sso_provider", None)
    monkeypatch.setattr(settings, "external_jwt_issuer", None)
    monkeypatch.setattr(settings, "external_jwt_audience", None)

    status = auth_status()

    assert status["provider"] == "mock"
    assert status["ready"] is True
    assert status["blockers"] == []


def test_auth_status_reports_external_jwt_blockers(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_provider", "external_jwt")
    monkeypatch.setattr(settings, "discovery_sso_provider", None)
    monkeypatch.setattr(settings, "external_jwt_issuer", None)
    monkeypatch.setattr(settings, "external_jwt_audience", None)
    monkeypatch.setattr(settings, "external_jwt_algorithms", [])

    status = auth_status()

    assert status["external_enabled"] is True
    assert status["ready"] is False
    assert status["blockers"] == [
        "discovery_sso_provider",
        "external_jwt_issuer",
        "external_jwt_audience",
        "external_jwt_algorithms",
    ]


def test_auth_status_reports_external_jwt_ready(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_provider", "external_jwt")
    monkeypatch.setattr(settings, "discovery_sso_provider", "approved-sso")
    monkeypatch.setattr(settings, "external_jwt_issuer", "https://idp.example.test")
    monkeypatch.setattr(settings, "external_jwt_audience", "phantom-vsa")
    monkeypatch.setattr(settings, "external_jwt_jwks_url", None)
    monkeypatch.setattr(settings, "external_jwt_algorithms", ["RS256"])

    status = auth_status()

    assert status["ready"] is True
    assert status["jwks_url_derived_from_issuer"] is True
    assert status["blockers"] == []


def test_auth_health_endpoint_reports_selected_provider(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_provider", "external_jwt")
    monkeypatch.setattr(settings, "discovery_sso_provider", "approved-sso")
    monkeypatch.setattr(settings, "external_jwt_issuer", None)
    monkeypatch.setattr(settings, "external_jwt_audience", "phantom-vsa")

    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/health/auth")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "external_jwt"
    assert body["ready"] is False
    assert body["blockers"] == ["external_jwt_issuer"]


def _rsa_jwk_and_private_key(kid: str = "test-key-1") -> tuple[dict, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "n": base64url_encode(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")).decode("ascii"),
        "e": base64url_encode(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")).decode("ascii"),
    }
    return jwk, private_key


def test_external_jwt_provider_validates_jwks_issuer_audience_and_claim_mapping(monkeypatch) -> None:
    jwk, private_key = _rsa_jwk_and_private_key()

    async def fake_fetch_jwks() -> dict:
        return {"keys": [jwk]}

    monkeypatch.setattr(settings, "auth_provider", "external_jwt")
    monkeypatch.setattr(settings, "discovery_sso_provider", "Azure AD")
    monkeypatch.setattr(settings, "external_jwt_issuer", "https://idp.example.test")
    monkeypatch.setattr(settings, "external_jwt_audience", "phantom-vsa")
    monkeypatch.setattr(settings, "external_jwt_jwks_url", "https://idp.example.test/keys")
    monkeypatch.setattr(settings, "external_jwt_role_claim", "roles")
    monkeypatch.setattr(settings, "external_jwt_territory_claim", "territory")
    monkeypatch.setattr(settings, "external_jwt_algorithms", ["RS256"])
    monkeypatch.setattr(providers, "fetch_jwks", fake_fetch_jwks)
    token = jwt.encode(
        {
            "sub": "REP-001",
            "iss": "https://idp.example.test",
            "aud": "phantom-vsa",
            "roles": ["rep"],
            "territory": "WEST-01",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": jwk["kid"]},
    )

    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as client:
        response = client.get("/api/v1/visits/today?territory_code=WEST-01")
    assert response.status_code == 200


def test_external_jwt_provider_rejects_wrong_audience(monkeypatch) -> None:
    jwk, private_key = _rsa_jwk_and_private_key()

    async def fake_fetch_jwks() -> dict:
        return {"keys": [jwk]}

    monkeypatch.setattr(settings, "auth_provider", "external_jwt")
    monkeypatch.setattr(settings, "discovery_sso_provider", "Okta")
    monkeypatch.setattr(settings, "external_jwt_issuer", "https://idp.example.test")
    monkeypatch.setattr(settings, "external_jwt_audience", "phantom-vsa")
    monkeypatch.setattr(settings, "external_jwt_jwks_url", "https://idp.example.test/keys")
    monkeypatch.setattr(settings, "external_jwt_role_claim", "role")
    monkeypatch.setattr(settings, "external_jwt_territory_claim", "territory_code")
    monkeypatch.setattr(settings, "external_jwt_algorithms", ["RS256"])
    monkeypatch.setattr(providers, "fetch_jwks", fake_fetch_jwks)
    token = jwt.encode(
        {
            "sub": "REP-001",
            "iss": "https://idp.example.test",
            "aud": "other-audience",
            "role": "rep",
            "territory_code": "WEST-01",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": jwk["kid"]},
    )

    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as client:
        response = client.get("/api/v1/visits/today?territory_code=WEST-01")
    assert response.status_code == 401


def test_mock_provider_still_authenticates(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_provider", "mock")
    with TestClient(app, headers={"Authorization": f"Bearer {REP_001}"}) as client:
        response = client.get("/api/v1/visits/today?territory_code=WEST-01")
    assert response.status_code == 200
