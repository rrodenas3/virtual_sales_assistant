from __future__ import annotations

from backend.adapters.factory import get_osa_data_port, get_shelf_image_port


async def analyze_shelf_image(
    store_id: str,
    rep_id: str,
    territory_code: str,
    image_ref: str,
    alert_ids: list[str] | None = None,
) -> dict:
    osa = get_osa_data_port()
    store = await osa.get_store_detail(rep_id, store_id)
    if store.territory_code != territory_code:
        raise ValueError("Store is outside the requested territory")
    alerts = await osa.get_alerts_by_ids(rep_id, territory_code, alert_ids)
    alerts = [alert for alert in alerts if alert.store_id == store_id]
    shelf_images = get_shelf_image_port()
    analysis_id, findings = await shelf_images.analyze(store_id=store_id, image_ref=image_ref, alerts=alerts)
    return {
        "analysis_id": analysis_id,
        "store_id": store_id,
        "findings": [finding.model_dump(mode="json") for finding in findings],
        "source_system": shelf_images.source_system,
        "model_version": shelf_images.model_version,
    }
