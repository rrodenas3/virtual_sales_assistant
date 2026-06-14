from __future__ import annotations

from backend.config import settings
from backend.memory.ports import MemoryPort


class NullMemoryAdapter:
    async def get_context(self, *, rep_id: str, store_id: str | None = None) -> dict:
        return {"provider": "none", "memories": [], "rep_id": rep_id, "store_id": store_id}

    async def record_interaction(self, *, rep_id: str, session_id: str, payload: dict) -> None:
        return None


class Mem0Adapter:
    def __init__(self) -> None:
        if not settings.mem0_token_ref:
            raise RuntimeError("Mem0 adapter missing setting: mem0_token_ref")

    async def get_context(self, *, rep_id: str, store_id: str | None = None) -> dict:
        raise NotImplementedError("Mem0 integration is deferred until memory scope and retention policy are confirmed")

    async def record_interaction(self, *, rep_id: str, session_id: str, payload: dict) -> None:
        raise NotImplementedError("Mem0 integration is deferred until memory scope and retention policy are confirmed")


def get_memory_adapter() -> MemoryPort:
    if settings.memory_provider == "none":
        return NullMemoryAdapter()
    return Mem0Adapter()
