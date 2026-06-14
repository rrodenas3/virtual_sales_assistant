from datetime import datetime, timezone

from backend.api.schemas import ConfidenceLabel


def action_and_confidence(
    *,
    risk_score: float,
    is_phantom_inventory: bool,
    data_freshness_ts: datetime,
    now: datetime | None = None,
) -> tuple[str, ConfidenceLabel]:
    now = now or datetime.now(timezone.utc)
    freshness = data_freshness_ts
    if freshness.tzinfo is None:
        freshness = freshness.replace(tzinfo=timezone.utc)

    if (now - freshness).total_seconds() > 24 * 60 * 60:
        return "Validate before acting - stale prediction", "low"
    if is_phantom_inventory and risk_score >= 0.85:
        return "Verify backroom inventory; escalate phantom signal", "high"
    if risk_score >= 0.9:
        return "Prioritize shelf check + replenishment draft", "high"
    if 0.7 <= risk_score < 0.9:
        return "Confirm on-shelf availability", "medium"
    return "Monitor during next visit", "low"


def priority_reasons(
    *,
    avg_oos_risk_score: float,
    promo_compliance_rate: float,
    revenue_opportunity_score: float,
    days_since_last_visit: int,
    oos_sku_count: int,
) -> list[str]:
    reasons: list[str] = []
    if avg_oos_risk_score >= 0.85:
        reasons.append(f"High OOS risk across {oos_sku_count} SKU alerts")
    elif avg_oos_risk_score >= 0.7:
        reasons.append(f"Moderate OOS risk across {oos_sku_count} SKU alerts")
    if promo_compliance_rate < 0.75:
        reasons.append("Promo compliance gap is material")
    if revenue_opportunity_score >= 0.75:
        reasons.append("High revenue opportunity store")
    if days_since_last_visit >= 14:
        reasons.append("Visit is overdue")
    return reasons or ["Routine coverage based on current territory plan"]

