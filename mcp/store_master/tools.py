from __future__ import annotations

from datetime import date

from backend.adapters.factory import get_osa_data_port, get_store_master_port


async def get_store_health(store_id: str) -> dict:
    store = await get_store_master_port().get_store_detail_any(store_id)
    return store.model_dump(mode="json")


async def get_territory_stores(territory_code: str, visit_date: str | None = None) -> list[dict]:
    rows = await get_osa_data_port().get_territory_store_summaries(
        territory_code,
        date.fromisoformat(visit_date) if visit_date else date.today(),
    )
    return [row.model_dump(mode="json") for row in rows]
