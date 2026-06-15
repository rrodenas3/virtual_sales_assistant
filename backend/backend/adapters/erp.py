from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from backend.config import Settings


@dataclass(frozen=True)
class ERPSubmitResult:
    erp_order_id: str
    status: str
    response_json: dict


class ERPPort(Protocol):
    async def submit_order(self, draft_id: str, payload: dict, approval_id: str, payload_hash: str) -> ERPSubmitResult:
        ...


class SandboxERPAdapter:
    async def submit_order(self, draft_id: str, payload: dict, approval_id: str, payload_hash: str) -> ERPSubmitResult:
        erp_order_id = f"SANDBOX-{draft_id[:8].upper()}"
        return ERPSubmitResult(
            erp_order_id=erp_order_id,
            status="SUBMITTED_SANDBOX",
            response_json={
                "erp_order_id": erp_order_id,
                "approval_id": approval_id,
                "payload_hash": payload_hash,
                "payload": payload,
            },
        )


class ExternalERPAdapter:
    def __init__(self, settings: Settings) -> None:
        missing = [name for name in ("erp_endpoint", "erp_token_ref") if not getattr(settings, name)]
        if missing:
            raise RuntimeError(f"External ERP adapter missing settings: {', '.join(missing)}")
        self.endpoint = settings.erp_endpoint
        self.token_ref = settings.erp_token_ref

    async def submit_order(self, draft_id: str, payload: dict, approval_id: str, payload_hash: str) -> ERPSubmitResult:
        request_payload = {
            "draft_id": draft_id,
            "approval_id": approval_id,
            "payload_hash": payload_hash,
            "payload": payload,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.endpoint.rstrip('/')}/orders",
                headers={"Authorization": f"Bearer {self.token_ref}"},
                json=request_payload,
            )
            response.raise_for_status()
        body = response.json()
        return ERPSubmitResult(
            erp_order_id=str(body.get("erp_order_id") or body.get("id")),
            status=str(body.get("status") or "SUBMITTED_EXTERNAL"),
            response_json=body,
        )
