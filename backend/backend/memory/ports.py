from __future__ import annotations

from typing import Protocol


class MemoryPort(Protocol):
    async def get_context(self, *, rep_id: str, store_id: str | None = None) -> dict:
        ...

    async def record_interaction(self, *, rep_id: str, session_id: str, payload: dict) -> None:
        ...
