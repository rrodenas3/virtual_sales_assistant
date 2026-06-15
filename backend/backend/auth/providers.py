from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, Protocol

import httpx
from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from backend.config import settings
from backend.governance.discovery import assert_discovery_ready


@dataclass(frozen=True)
class CurrentUser:
    sub: str
    role: Literal["rep", "manager", "admin"]
    territory_code: str | None = None

    @property
    def rep_id(self) -> str:
        return self.sub


class AuthProvider(Protocol):
    async def authenticate(self, request: Request) -> CurrentUser:
        ...


def _extract_bearer_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return token


def _decode_segment(segment: str) -> dict:
    padded = segment + "=" * (-len(segment) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def _user_from_claims(claims: dict, *, role_claim: str = "role", territory_claim: str = "territory_code") -> CurrentUser:
    role = claims.get(role_claim)
    if isinstance(role, list):
        role = next((item for item in role if item in {"rep", "manager", "admin"}), None)
    if role not in {"rep", "manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid role")
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing subject")
    return CurrentUser(sub=sub, role=role, territory_code=claims.get(territory_claim))


class MockJWTProvider:
    async def authenticate(self, request: Request) -> CurrentUser:
        return parse_mock_jwt(_extract_bearer_token(request))


def parse_mock_jwt(token: str) -> CurrentUser:
    parts = token.split(".")
    if len(parts) < 2:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return _user_from_claims(_decode_segment(parts[1]))


class ExternalJWTProvider:
    async def authenticate(self, request: Request) -> CurrentUser:
        token = _extract_bearer_token(request)
        try:
            assert_discovery_ready("external_jwt")
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        if not settings.external_jwt_issuer or not settings.external_jwt_audience:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="External JWT provider is not configured")
        try:
            claims = await validate_external_jwt(token)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid external token") from exc
        return _user_from_claims(
            claims,
            role_claim=settings.external_jwt_role_claim,
            territory_claim=settings.external_jwt_territory_claim,
        )


def _jwks_url() -> str:
    if settings.external_jwt_jwks_url:
        return settings.external_jwt_jwks_url
    if not settings.external_jwt_issuer:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="External JWT issuer is not configured")
    return f"{settings.external_jwt_issuer.rstrip('/')}/.well-known/jwks.json"


@lru_cache(maxsize=8)
def _cached_jwks_url(url: str) -> str:
    return url


async def fetch_jwks() -> dict:
    url = _cached_jwks_url(_jwks_url())
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Unable to fetch external JWT JWKS") from exc
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("keys"), list):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="External JWT JWKS is invalid")
    return body


async def validate_external_jwt(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid external token header") from exc
    kid = header.get("kid")
    alg = header.get("alg")
    if alg not in settings.external_jwt_algorithms:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unsupported external token algorithm")

    jwks = await fetch_jwks()
    key = next((item for item in jwks["keys"] if item.get("kid") == kid), None)
    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown external token key")
    try:
        return jwt.decode(
            token,
            key,
            algorithms=settings.external_jwt_algorithms,
            audience=settings.external_jwt_audience,
            issuer=settings.external_jwt_issuer,
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid external token") from exc


def get_auth_provider() -> AuthProvider:
    if settings.auth_provider == "mock":
        return MockJWTProvider()
    return ExternalJWTProvider()


def auth_status() -> dict:
    blockers: list[str] = []
    if settings.auth_provider == "external_jwt":
        if not settings.discovery_sso_provider:
            blockers.append("discovery_sso_provider")
        if not settings.external_jwt_issuer:
            blockers.append("external_jwt_issuer")
        if not settings.external_jwt_audience:
            blockers.append("external_jwt_audience")
        if not settings.external_jwt_algorithms:
            blockers.append("external_jwt_algorithms")

    return {
        "provider": settings.auth_provider,
        "external_enabled": settings.auth_provider == "external_jwt",
        "issuer_configured": bool(settings.external_jwt_issuer),
        "audience_configured": bool(settings.external_jwt_audience),
        "jwks_url_configured": bool(settings.external_jwt_jwks_url),
        "jwks_url_derived_from_issuer": bool(settings.external_jwt_issuer and not settings.external_jwt_jwks_url),
        "role_claim": settings.external_jwt_role_claim,
        "territory_claim": settings.external_jwt_territory_claim,
        "algorithms_configured": bool(settings.external_jwt_algorithms),
        "discovery_configured": bool(settings.discovery_sso_provider),
        "ready": not blockers,
        "blockers": blockers,
    }


async def get_current_user(request: Request) -> CurrentUser:
    return await get_auth_provider().authenticate(request)
