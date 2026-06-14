from backend.api.schemas import OOSAlert


def build_grounded_summary(alerts: list[OOSAlert]) -> str:
    if not alerts:
        return "No grounded OOS alerts are available for this request."
    sorted_alerts = sorted(alerts, key=lambda alert: (-alert.risk_score, alert.sku_id))
    top = sorted_alerts[:5]
    lines = [
        f"{len(alerts)} grounded OOS alerts are active. Top risks:",
    ]
    for alert in top:
        percent = round(alert.risk_score * 100)
        lines.append(
            f"- {alert.sku_name} at {alert.store_id}: {percent}% risk, "
            f"{alert.root_cause_label}; action: {alert.recommended_action}."
        )
    return "\n".join(lines)

