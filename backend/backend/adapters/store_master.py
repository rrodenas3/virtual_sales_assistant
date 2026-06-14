from __future__ import annotations

from typing import Protocol

from backend.adapters.osa import MockOSAAdapter
from backend.api.schemas import StoreDetail


class StoreMasterPort(Protocol):
    async def get_store_detail_any(self, store_id: str) -> StoreDetail:
        ...


class MockStoreMasterAdapter:
    source_system = "mock-store-master"

    def __init__(self, osa: MockOSAAdapter | None = None) -> None:
        self._osa = osa or MockOSAAdapter()

    async def get_store_detail_any(self, store_id: str) -> StoreDetail:
        return await self._osa.get_store_detail_any(store_id)
