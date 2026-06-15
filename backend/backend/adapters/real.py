from __future__ import annotations

from datetime import date, datetime
from typing import Any

from backend.api.schemas import (
    AssortmentGap,
    OOSAlert,
    PromoRecommendation,
    StoreDetail,
    TerritoryStoreSummary,
    UpsellOpportunity,
    VisitComponents,
    VisitPriority,
)
from backend.clients.sql import DatabricksSQLClient, QueryStatement, SQLClient, SnowflakeSQLClient, param
from backend.config import Settings
from backend.services.rules import action_and_confidence, priority_reasons


def _missing(names: list[str], settings: Settings) -> list[str]:
    return [name for name in names if not getattr(settings, name)]


def _dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _date_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _float(value: Any) -> float:
    return float(value)


def _int(value: Any) -> int:
    return int(value)


def _stable_alert_id(row: dict[str, Any]) -> str:
    prediction_date = _dt(row["data_freshness_ts"]).date().isoformat()
    return f"{row['store_id']}:{row['sku_id']}:{prediction_date}"


class DatabricksOSAAdapter:
    source_system = "databricks"
    model_version = "databricks-pending"

    def __init__(self, settings: Settings, client: SQLClient | None = None) -> None:
        missing = _missing(["databricks_host", "databricks_token", "databricks_sql_warehouse_id"], settings)
        if missing:
            raise RuntimeError(f"Databricks OSA adapter missing settings: {', '.join(missing)}")
        self.client = client or DatabricksSQLClient(settings)

    async def get_visit_priority(self, rep_id: str, territory_code: str, visit_date: date) -> list[VisitPriority]:
        rows = await self.client.execute(
            QueryStatement(
                statement="""
SELECT store_id, store_name, address, avg_oos_risk_score, promo_compliance_rate,
       revenue_opportunity_score, days_since_last_visit, oos_sku_count, data_freshness_ts
FROM osa_visit_priority
WHERE rep_id = :rep_id AND territory_code = :territory_code AND visit_date = :visit_date
ORDER BY priority_score DESC, oos_sku_count DESC, store_id ASC
""".strip(),
                parameters=(
                    param("rep_id", rep_id),
                    param("territory_code", territory_code),
                    param("visit_date", visit_date),
                ),
            )
        )
        visits: list[VisitPriority] = []
        for row in rows:
            avg_oos = _float(row["avg_oos_risk_score"])
            promo = _float(row["promo_compliance_rate"])
            revenue = _float(row["revenue_opportunity_score"])
            days_since = _int(row["days_since_last_visit"])
            components = VisitComponents(
                oos_risk=round(avg_oos, 3),
                promo_gap=round(1 - promo, 3),
                revenue_opportunity=round(revenue, 3),
                visit_recency=round(min(max(days_since, 0) / 30, 1.0), 3),
            )
            priority_score = round(
                0.4 * components.oos_risk
                + 0.3 * components.promo_gap
                + 0.2 * components.revenue_opportunity
                + 0.1 * components.visit_recency,
                3,
            )
            visits.append(
                VisitPriority(
                    store_id=str(row["store_id"]),
                    store_name=str(row["store_name"]),
                    address=str(row["address"]),
                    priority_score=priority_score,
                    rank=0,
                    reasons=priority_reasons(
                        avg_oos_risk_score=avg_oos,
                        promo_compliance_rate=promo,
                        revenue_opportunity_score=revenue,
                        days_since_last_visit=days_since,
                        oos_sku_count=_int(row["oos_sku_count"]),
                    ),
                    components=components,
                    oos_sku_count=_int(row["oos_sku_count"]),
                    data_freshness_ts=_dt(row["data_freshness_ts"]),
                )
            )
        visits.sort(key=lambda item: (-item.priority_score, -item.oos_sku_count, item.store_id))
        return [visit.model_copy(update={"rank": idx + 1}) for idx, visit in enumerate(visits)]

    async def get_oos_alerts(
        self,
        rep_id: str,
        store_id: str,
        min_risk_score: float,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[OOSAlert], str | None]:
        offset = int(cursor or "0")
        rows = await self.client.execute(
            QueryStatement(
                statement="""
SELECT prediction_row_id, store_id, sku_id, sku_name, category, risk_score, is_phantom_inventory,
       predicted_stockout_date, root_cause_label, data_freshness_ts
FROM osa_oos_alerts
WHERE rep_id = :rep_id AND store_id = :store_id AND risk_score >= :min_risk_score
ORDER BY risk_score DESC, sku_id ASC
LIMIT :limit OFFSET :offset
""".strip(),
                parameters=(
                    param("rep_id", rep_id),
                    param("store_id", store_id),
                    param("min_risk_score", min_risk_score, "DOUBLE"),
                    param("limit", limit, "INT"),
                    param("offset", offset, "INT"),
                ),
            )
        )
        next_cursor = str(offset + limit) if len(rows) == limit else None
        return [self._alert_from_row(row) for row in rows], next_cursor

    async def get_store_detail(self, rep_id: str, store_id: str) -> StoreDetail:
        rows = await self.client.execute(
            QueryStatement(
                statement="""
SELECT store_id, store_name, retailer_name, address, store_tier, territory_code, rep_id,
       last_visit_date, next_visit_date, units_sold_30d, revenue_30d, promo_compliance_rate,
       revenue_opportunity_score, oos_sku_count, data_freshness_ts
FROM osa_store_detail
WHERE rep_id = :rep_id AND store_id = :store_id
LIMIT 1
""".strip(),
                parameters=(param("rep_id", rep_id), param("store_id", store_id)),
            )
        )
        if not rows:
            raise KeyError(store_id)
        return self._store_from_row(rows[0])

    async def get_alerts_by_ids(self, rep_id: str, territory_code: str, alert_ids: list[str] | None) -> list[OOSAlert]:
        params = [param("rep_id", rep_id), param("territory_code", territory_code)]
        alert_filter = ""
        if alert_ids is not None:
            alert_filter = "AND alert_id IN (" + ", ".join(f":alert_id_{idx}" for idx in range(len(alert_ids))) + ")"
            params.extend(param(f"alert_id_{idx}", alert_id) for idx, alert_id in enumerate(alert_ids))
        rows = await self.client.execute(
            QueryStatement(
                statement=f"""
SELECT prediction_row_id, store_id, sku_id, sku_name, category, risk_score, is_phantom_inventory,
       predicted_stockout_date, root_cause_label, data_freshness_ts
FROM osa_oos_alerts
WHERE rep_id = :rep_id AND territory_code = :territory_code {alert_filter}
ORDER BY risk_score DESC, sku_id ASC
""".strip(),
                parameters=tuple(params),
            )
        )
        return [self._alert_from_row(row) for row in rows]

    async def get_store_detail_any(self, store_id: str) -> StoreDetail:
        rows = await self.client.execute(
            QueryStatement(
                statement="""
SELECT store_id, store_name, retailer_name, address, store_tier, territory_code, rep_id,
       last_visit_date, next_visit_date, units_sold_30d, revenue_30d, promo_compliance_rate,
       revenue_opportunity_score, oos_sku_count, data_freshness_ts
FROM osa_store_detail
WHERE store_id = :store_id
LIMIT 1
""".strip(),
                parameters=(param("store_id", store_id),),
            )
        )
        if not rows:
            raise KeyError(store_id)
        return self._store_from_row(rows[0])

    async def get_territory_store_summaries(self, territory_code: str, visit_date: date) -> list[TerritoryStoreSummary]:
        rows = await self.client.execute(
            QueryStatement(
                statement="""
SELECT store_id, store_name, rep_id, priority_score, oos_sku_count, confirmed_feedback_count,
       false_positive_count, open_draft_count, data_freshness_ts
FROM osa_territory_store_summary
WHERE territory_code = :territory_code AND visit_date = :visit_date
ORDER BY priority_score DESC, oos_sku_count DESC, store_id ASC
""".strip(),
                parameters=(param("territory_code", territory_code), param("visit_date", visit_date)),
            )
        )
        return [
            TerritoryStoreSummary(
                store_id=str(row["store_id"]),
                store_name=str(row["store_name"]),
                rep_id=str(row["rep_id"]),
                priority_score=_float(row["priority_score"]),
                oos_sku_count=_int(row["oos_sku_count"]),
                confirmed_feedback_count=_int(row.get("confirmed_feedback_count", 0)),
                false_positive_count=_int(row.get("false_positive_count", 0)),
                open_draft_count=_int(row.get("open_draft_count", 0)),
                data_freshness_ts=_dt(row["data_freshness_ts"]),
            )
            for row in rows
        ]

    def _store_from_row(self, row: dict[str, Any]) -> StoreDetail:
        return StoreDetail(
            store_id=str(row["store_id"]),
            store_name=str(row["store_name"]),
            retailer_name=str(row["retailer_name"]),
            address=str(row["address"]),
            store_tier=str(row["store_tier"]),  # type: ignore[arg-type]
            territory_code=str(row["territory_code"]),
            rep_id=str(row["rep_id"]),
            last_visit_date=_date_str(row.get("last_visit_date")),
            next_visit_date=_date_str(row.get("next_visit_date")),
            units_sold_30d=_int(row["units_sold_30d"]),
            revenue_30d=_float(row["revenue_30d"]),
            promo_compliance_rate=_float(row["promo_compliance_rate"]),
            revenue_opportunity_score=_float(row["revenue_opportunity_score"]),
            oos_sku_count=_int(row["oos_sku_count"]),
            data_freshness_ts=_dt(row["data_freshness_ts"]),
        )

    def _alert_from_row(self, row: dict[str, Any]) -> OOSAlert:
        risk_score = _float(row["risk_score"])
        is_phantom = bool(row["is_phantom_inventory"])
        data_freshness_ts = _dt(row["data_freshness_ts"])
        recommended_action, confidence_label = action_and_confidence(
            risk_score=risk_score,
            is_phantom_inventory=is_phantom,
            data_freshness_ts=data_freshness_ts,
        )
        return OOSAlert(
            alert_id=str(row.get("alert_id") or _stable_alert_id(row)),
            prediction_row_id=str(row["prediction_row_id"]),
            store_id=str(row["store_id"]),
            sku_id=str(row["sku_id"]),
            sku_name=str(row["sku_name"]),
            category=str(row["category"]),
            risk_score=risk_score,
            is_phantom_inventory=is_phantom,
            predicted_stockout_date=_date_str(row.get("predicted_stockout_date")),
            root_cause_label=str(row["root_cause_label"]),
            recommended_action=recommended_action,
            confidence_label=confidence_label,
            data_freshness_ts=data_freshness_ts,
            model_version=self.model_version,
            source_system=self.source_system,
        )


class DatabricksRGMAdapter:
    source_system = "databricks"
    model_version = "databricks-rgm-pending"

    def __init__(self, settings: Settings, client: SQLClient | None = None) -> None:
        missing = _missing(["databricks_host", "databricks_token", "databricks_sql_warehouse_id"], settings)
        if missing:
            raise RuntimeError(f"Databricks RGM adapter missing settings: {', '.join(missing)}")
        self.client = client or DatabricksSQLClient(settings)

    async def get_recommendations(
        self,
        store_id: str,
        revenue_opportunity_score: float,
        promo_compliance_rate: float,
    ) -> tuple[list[PromoRecommendation], list[AssortmentGap], list[UpsellOpportunity]]:
        rows = await self.client.execute(
            QueryStatement(
                statement="""
SELECT recommendation_type, recommendation_id, store_id, sku_id, sku_name, category, promo_name,
       expected_lift, margin_impact, estimated_revenue_opportunity, estimated_value, reason, confidence_label
FROM rgm_recommendations
WHERE store_id = :store_id
ORDER BY recommendation_type, recommendation_id
""".strip(),
                parameters=(param("store_id", store_id),),
            )
        )
        promos: list[PromoRecommendation] = []
        gaps: list[AssortmentGap] = []
        upsells: list[UpsellOpportunity] = []
        for row in rows:
            kind = row["recommendation_type"]
            if kind == "promo":
                promos.append(
                    PromoRecommendation(
                        recommendation_id=str(row["recommendation_id"]),
                        store_id=str(row["store_id"]),
                        sku_id=str(row["sku_id"]),
                        promo_name=str(row["promo_name"]),
                        expected_lift=_float(row["expected_lift"]),
                        margin_impact=_float(row["margin_impact"]),
                        reason=str(row["reason"]),
                        confidence_label=str(row["confidence_label"]),  # type: ignore[arg-type]
                    )
                )
            elif kind == "assortment_gap":
                gaps.append(
                    AssortmentGap(
                        gap_id=str(row["recommendation_id"]),
                        store_id=str(row["store_id"]),
                        sku_id=str(row["sku_id"]),
                        sku_name=str(row["sku_name"]),
                        category=str(row["category"]),
                        estimated_revenue_opportunity=_float(row["estimated_revenue_opportunity"]),
                        reason=str(row["reason"]),
                        confidence_label=str(row["confidence_label"]),  # type: ignore[arg-type]
                    )
                )
            elif kind == "upsell":
                upsells.append(
                    UpsellOpportunity(
                        opportunity_id=str(row["recommendation_id"]),
                        store_id=str(row["store_id"]),
                        sku_id=str(row["sku_id"]),
                        sku_name=str(row["sku_name"]),
                        estimated_value=_float(row["estimated_value"]),
                        reason=str(row["reason"]),
                        confidence_label=str(row["confidence_label"]),  # type: ignore[arg-type]
                    )
                )
        return promos, gaps, upsells


class SnowflakeStoreMasterAdapter:
    source_system = "snowflake"

    def __init__(self, settings: Settings, client: SQLClient | None = None) -> None:
        missing = _missing(
            ["snowflake_account", "snowflake_user", "snowflake_warehouse", "snowflake_database", "snowflake_schema"],
            settings,
        )
        if missing:
            raise RuntimeError(f"Snowflake store master adapter missing settings: {', '.join(missing)}")
        self.client = client or SnowflakeSQLClient(settings)

    async def get_store_detail_any(self, store_id: str) -> StoreDetail:
        rows = await self.client.execute(
            QueryStatement(
                statement="""
SELECT store_id, store_name, retailer_name, address, store_tier, territory_code, rep_id,
       last_visit_date, next_visit_date, units_sold_30d, revenue_30d, promo_compliance_rate,
       revenue_opportunity_score, oos_sku_count, data_freshness_ts
FROM store_master
WHERE store_id = :store_id
LIMIT 1
""".strip(),
                parameters=(param("store_id", store_id),),
            )
        )
        if not rows:
            raise KeyError(store_id)
        return DatabricksOSAAdapter._store_from_row(self, rows[0])
