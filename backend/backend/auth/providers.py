from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Literal, Protocol

from fastapi import HTTPException, Request, status

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


def _user_from_claims(claims: dict) -> CurrentUser:
    role = claims.get("role")
    if role not in {"rep", "manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid role")
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing subject")
    return CurrentUser(sub=sub, role=role, territory_code=claims.get("territory_code"))


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
        _extract_bearer_token(request)
        try:
            assert_discovery_ready("external_jwt")
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        if not settings.external_jwt_issuer or not settings.external_jwt_audience:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="External JWT provider is not configured")
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="External JWT validation is not implemented")


def get_auth_provider() -> AuthProvider:
    if settings.auth_provider == "mock":
        return MockJWTProvider()
    return ExternalJWTProvider()


async def get_current_user(request: Request) -> CurrentUser:
    return await get_auth_provider().authenticate(request)
