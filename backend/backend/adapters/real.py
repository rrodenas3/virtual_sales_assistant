from __future__ import annotations

from datetime import date

from backend.api.schemas import AssortmentGap, OOSAlert, PromoRecommendation, StoreDetail, TerritoryStoreSummary, UpsellOpportunity, VisitPriority
from backend.config import Settings


def _missing(names: list[str], settings: Settings) -> list[str]:
    return [name for name in names if not getattr(settings, name)]


class DatabricksOSAAdapter:
    source_system = "databricks"
    model_version = "databricks-pending"

    def __init__(self, settings: Settings) -> None:
        missing = _missing(["databricks_host", "databricks_token", "databricks_sql_warehouse_id"], settings)
        if missing:
            raise RuntimeError(f"Databricks OSA adapter missing settings: {', '.join(missing)}")

    async def get_visit_priority(self, rep_id: str, territory_code: str, visit_date: date) -> list[VisitPriority]:
        raise NotImplementedError("Databricks OSA adapter is scaffolded until client SQL contracts are confirmed")

    async def get_oos_alerts(
        self,
        rep_id: str,
        store_id: str,
        min_risk_score: float,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[OOSAlert], str | None]:
        raise NotImplementedError("Databricks OSA adapter is scaffolded until client SQL contracts are confirmed")

    async def get_store_detail(self, rep_id: str, store_id: str) -> StoreDetail:
        raise NotImplementedError("Databricks OSA adapter is scaffolded until client SQL contracts are confirmed")

    async def get_alerts_by_ids(self, rep_id: str, territory_code: str, alert_ids: list[str] | None) -> list[OOSAlert]:
        raise NotImplementedError("Databricks OSA adapter is scaffolded until client SQL contracts are confirmed")

    async def get_store_detail_any(self, store_id: str) -> StoreDetail:
        raise NotImplementedError("Databricks OSA adapter is scaffolded until client SQL contracts are confirmed")

    async def get_territory_store_summaries(self, territory_code: str, visit_date: date) -> list[TerritoryStoreSummary]:
        raise NotImplementedError("Databricks OSA adapter is scaffolded until client SQL contracts are confirmed")


class DatabricksRGMAdapter:
    source_system = "databricks"
    model_version = "databricks-rgm-pending"

    def __init__(self, settings: Settings) -> None:
        missing = _missing(["databricks_host", "databricks_token", "databricks_sql_warehouse_id"], settings)
        if missing:
            raise RuntimeError(f"Databricks RGM adapter missing settings: {', '.join(missing)}")

    async def get_recommendations(
        self,
        store_id: str,
        revenue_opportunity_score: float,
        promo_compliance_rate: float,
    ) -> tuple[list[PromoRecommendation], list[AssortmentGap], list[UpsellOpportunity]]:
        raise NotImplementedError("Databricks RGM adapter is scaffolded until client SQL contracts are confirmed")


class SnowflakeStoreMasterAdapter:
    source_system = "snowflake"

    def __init__(self, settings: Settings) -> None:
        missing = _missing(
            ["snowflake_account", "snowflake_user", "snowflake_warehouse", "snowflake_database", "snowflake_schema"],
            settings,
        )
        if missing:
            raise RuntimeError(f"Snowflake store master adapter missing settings: {', '.join(missing)}")

    async def get_store_detail_any(self, store_id: str) -> StoreDetail:
        raise NotImplementedError("Snowflake store master adapter is scaffolded until client view contracts are confirmed")
