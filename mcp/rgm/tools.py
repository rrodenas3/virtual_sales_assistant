from __future__ import annotations

from backend.adapters.factory import get_osa_data_port, get_rgm_data_port


async def get_rgm_recommendations(store_id: str) -> dict:
    store = await get_osa_data_port().get_store_detail_any(store_id)
    promos, gaps, upsells = await get_rgm_data_port().get_recommendations(
        store_id,
        store.revenue_opportunity_score,
        store.promo_compliance_rate,
    )
    rgm = get_rgm_data_port()
    return {
        "store_id": store_id,
        "promos": [row.model_dump(mode="json") for row in promos],
        "assortment_gaps": [row.model_dump(mode="json") for row in gaps],
        "upsell_opportunities": [row.model_dump(mode="json") for row in upsells],
        "source_system": rgm.source_system,
        "model_version": rgm.model_version,
    }
