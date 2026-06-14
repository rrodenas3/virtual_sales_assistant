from __future__ import annotations

from datetime import date

from backend.adapters.factory import get_osa_data_port


def _dump_list(rows: list) -> list[dict]:
    return [row.model_dump(mode="json") for row in rows]


async def get_visit_priority(rep_id: str, territory_code: str, visit_date: str) -> list[dict]:
    rows = await get_osa_data_port().get_visit_priority(rep_id, territory_code, date.fromisoformat(visit_date))
    return _dump_list(rows)


async def get_oos_alerts(
    rep_id: str,
    store_id: str,
    min_risk_score: float = 0.7,
    limit: int = 50,
    cursor: str | None = None,
) -> dict:
    alerts, next_cursor = await get_osa_data_port().get_oos_alerts(rep_id, store_id, min_risk_score, limit, cursor)
    return {
        "alerts": _dump_list(alerts),
        "page": {"next_cursor": next_cursor, "limit": limit},
    }


async def get_phantom_inventory(rep_id: str, store_id: str, min_risk_score: float = 0.7) -> list[dict]:
    alerts, _ = await get_osa_data_port().get_oos_alerts(rep_id, store_id, min_risk_score, 100, None)
    return _dump_list([alert for alert in alerts if alert.is_phantom_inventory])
