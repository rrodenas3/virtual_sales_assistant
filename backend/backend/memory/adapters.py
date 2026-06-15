from __future__ import annotations

import httpx

from backend.config import settings
from backend.governance.discovery import assert_discovery_ready
from backend.memory.ports import MemoryPort


class NullMemoryAdapter:
    async def get_context(self, *, rep_id: str, store_id: str | None = None) -> dict:
        return {"provider": "none", "memories": [], "rep_id": rep_id, "store_id": store_id}

    async def record_interaction(self, *, rep_id: str, session_id: str, payload: dict) -> None:
        return None


class Mem0Adapter:
    def __init__(self) -> None:
        assert_discovery_ready("mem0")
        if not settings.mem0_token_ref:
            raise RuntimeError("Mem0 adapter missing setting: mem0_token_ref")
        self.endpoint = settings.mem0_endpoint.rstrip("/")
        self.token_ref = settings.mem0_token_ref

    async def get_context(self, *, rep_id: str, store_id: str | None = None) -> dict:
        payload = {
            "user_id": rep_id,
            "filters": {"store_id": store_id} if store_id else {},
            "limit": 5,
        }
        async with httpx.AsyncClient(timeout=settings.mem0_timeout_seconds) as client:
            response = await client.post(
                f"{self.endpoint}/memories/search",
                headers={"Authorization": f"Bearer {self.token_ref}"},
                json=payload,
            )
            response.raise_for_status()
        body = response.json()
        memories = body.get("memories", body.get("results", []))
        return {
            "provider": "mem0",
            "rep_id": rep_id,
            "store_id": store_id,
            "memories": memories if isinstance(memories, list) else [],
        }

    async def record_interaction(self, *, rep_id: str, session_id: str, payload: dict) -> None:
        memory_payload = {
            "user_id": rep_id,
            "metadata": {
                "session_id": session_id,
                "store_id": payload.get("store_id"),
                "event_type": payload.get("event_type"),
            },
            "messages": [
                {
                    "role": "assistant",
                    "content": str(payload.get("summary") or payload.get("event_type") or "interaction recorded"),
                }
            ],
        }
        async with httpx.AsyncClient(timeout=settings.mem0_timeout_seconds) as client:
            response = await client.post(
                f"{self.endpoint}/memories",
                headers={"Authorization": f"Bearer {self.token_ref}"},
                json=memory_payload,
            )
            response.raise_for_status()


def get_memory_adapter() -> MemoryPort:
    if settings.memory_provider == "none":
        return NullMemoryAdapter()
    return Mem0Adapter()
