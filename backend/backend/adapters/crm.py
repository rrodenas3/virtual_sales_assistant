from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from backend.config import Settings


@dataclass(frozen=True)
class VisitLogSubmitResult:
    external_id: str | None
    status: str
    response_json: dict


class CRMPort(Protocol):
    async def submit_visit_log(self, payload: dict) -> VisitLogSubmitResult:
        ...


class LocalCRMAdapter:
    async def submit_visit_log(self, payload: dict) -> VisitLogSubmitResult:
        return VisitLogSubmitResult(external_id=None, status="DRAFT", response_json=payload)


class ExternalCRMAdapter:
    def __init__(self, settings: Settings) -> None:
        missing = [name for name in ("crm_endpoint", "crm_token_ref") if not getattr(settings, name)]
        if missing:
            raise RuntimeError(f"External CRM adapter missing settings: {', '.join(missing)}")
        self.endpoint = settings.crm_endpoint
        self.token_ref = settings.crm_token_ref

    async def submit_visit_log(self, payload: dict) -> VisitLogSubmitResult:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.endpoint.rstrip('/')}/visit-logs",
                headers={"Authorization": f"Bearer {self.token_ref}"},
                json=payload,
            )
            response.raise_for_status()
        body = response.json()
        return VisitLogSubmitResult(
            external_id=body.get("external_id") or body.get("id"),
            status=str(body.get("status") or "SUBMITTED"),
            response_json=body,
        )
