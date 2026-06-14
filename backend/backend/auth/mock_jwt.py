import base64
import json
from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class CurrentUser:
    sub: str
    role: Literal["rep", "manager", "admin"]
    territory_code: str | None = None

    @property
    def rep_id(self) -> str:
        return self.sub


def _decode_segment(segment: str) -> dict:
    padded = segment + "=" * (-len(segment) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def parse_mock_jwt(token: str) -> CurrentUser:
    parts = token.split(".")
    if len(parts) < 2:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    claims = _decode_segment(parts[1])
    role = claims.get("role")
    if role not in {"rep", "manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid role")
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing subject")
    return CurrentUser(sub=sub, role=role, territory_code=claims.get("territory_code"))


async def get_current_user(request: Request) -> CurrentUser:
    auth = request.headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return parse_mock_jwt(token)

