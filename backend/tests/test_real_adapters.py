from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from backend.adapters.real import DatabricksOSAAdapter, DatabricksRGMAdapter, SnowflakeStoreMasterAdapter
from backend.clients.sql import QueryStatement
from backend.config import settings


class FakeSQLClient:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.queries: list[QueryStatement] = []

    async def execute(self, query: QueryStatement) -> list[dict[str, Any]]:
        self.queries.append(query)
        return self.rows


def _configure_databricks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "databricks_host", "https://dbc.example.test")
    monkeypatch.setattr(settings, "databricks_token", "token")
    monkeypatch.setattr(settings, "databricks_sql_warehouse_id", "warehouse")


def _configure_snowflake(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "snowflake_account", "acct")
    monkeypatch.setattr(settings, "snowflake_user", "user")
    monkeypatch.setattr(settings, "snowflake_warehouse", "wh")
    monkeypatch.setattr(settings, "snowflake_database", "db")
    monkeypatch.setattr(settings, "snowflake_schema", "schema")


@pytest.mark.asyncio
async def test_databricks_visit_priority_uses_parameters_not_interpolated_values(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_databricks(monkeypatch)
    client = FakeSQLClient(
        [
            {
                "store_id": "ST-001",
                "store_name": "West Market 01",
                "address": "101 Commerce Ave",
                "avg_oos_risk_score": 0.9,
                "promo_compliance_rate": 0.7,
                "revenue_opportunity_score": 0.8,
                "days_since_last_visit": 12,
                "oos_sku_count": 4,
                "data_freshness_ts": "2026-06-15T00:00:00+00:00",
            }
        ]
    )
    adapter = DatabricksOSAAdapter(settings, client=client)

    rows = await adapter.get_visit_priority("REP-001", "WEST-01", date(2026, 6, 15))

    query = client.queries[0]
    assert "REP-001" not in query.statement
    assert "WEST-01" not in query.statement
    assert {param.name: param.value for param in query.parameters} == {
        "rep_id": "REP-001",
        "territory_code": "WEST-01",
        "visit_date": "2026-06-15",
    }
    assert rows[0].store_id == "ST-001"
    assert rows[0].rank == 1
    assert rows[0].priority_score == 0.65


@pytest.mark.asyncio
async def test_databricks_alert_query_paginates_with_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_databricks(monkeypatch)
    client = FakeSQLClient(
        [
            {
                "prediction_row_id": "PRED-00001",
                "store_id": "ST-001",
                "sku_id": "SKU-4001",
                "sku_name": "Core SKU 4001",
                "category": "Beverages",
                "risk_score": 0.91,
                "is_phantom_inventory": True,
                "predicted_stockout_date": "2026-06-16",
                "root_cause_label": "phantom",
                "data_freshness_ts": "2026-06-15T00:00:00+00:00",
            }
        ]
    )
    adapter = DatabricksOSAAdapter(settings, client=client)

    alerts, next_cursor = await adapter.get_oos_alerts("REP-001", "ST-001", min_risk_score=0.8, limit=50, cursor=None)

    query = client.queries[0]
    assert "ST-001" not in query.statement
    assert {param.name for param in query.parameters} == {"rep_id", "store_id", "min_risk_score", "limit", "offset"}
    assert next_cursor is None
    assert alerts[0].alert_id == "ST-001:SKU-4001:2026-06-15"
    assert alerts[0].recommended_action


@pytest.mark.asyncio
async def test_databricks_rgm_adapter_maps_recommendation_types(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_databricks(monkeypatch)
    client = FakeSQLClient(
        [
            {
                "recommendation_type": "promo",
                "recommendation_id": "PROMO-1",
                "store_id": "ST-001",
                "sku_id": "SKU-4001",
                "sku_name": "Core SKU 4001",
                "category": "Beverages",
                "promo_name": "Endcap recovery",
                "expected_lift": 0.12,
                "margin_impact": 0.04,
                "estimated_revenue_opportunity": None,
                "estimated_value": None,
                "reason": "Promo gap",
                "confidence_label": "high",
            },
            {
                "recommendation_type": "assortment_gap",
                "recommendation_id": "GAP-1",
                "store_id": "ST-001",
                "sku_id": "SKU-4002",
                "sku_name": "Core SKU 4002",
                "category": "Beverages",
                "promo_name": None,
                "expected_lift": None,
                "margin_impact": None,
                "estimated_revenue_opportunity": 1200,
                "estimated_value": None,
                "reason": "Peer velocity",
                "confidence_label": "medium",
            },
        ]
    )
    adapter = DatabricksRGMAdapter(settings, client=client)

    promos, gaps, upsells = await adapter.get_recommendations("ST-001", 0.8, 0.7)

    assert "ST-001" not in client.queries[0].statement
    assert promos[0].recommendation_id == "PROMO-1"
    assert gaps[0].gap_id == "GAP-1"
    assert upsells == []


@pytest.mark.asyncio
async def test_snowflake_store_master_uses_store_id_parameter(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_snowflake(monkeypatch)
    client = FakeSQLClient(
        [
            {
                "store_id": "ST-001",
                "store_name": "West Market 01",
                "retailer_name": "Northstar Retail",
                "address": "101 Commerce Ave",
                "store_tier": "A",
                "territory_code": "WEST-01",
                "rep_id": "REP-001",
                "last_visit_date": "2026-06-01",
                "next_visit_date": "2026-06-20",
                "units_sold_30d": 1200,
                "revenue_30d": 24000,
                "promo_compliance_rate": 0.77,
                "revenue_opportunity_score": 0.75,
                "oos_sku_count": 5,
                "data_freshness_ts": "2026-06-15T00:00:00+00:00",
            }
        ]
    )
    adapter = SnowflakeStoreMasterAdapter(settings, client=client)

    store = await adapter.get_store_detail_any("ST-001")

    assert "ST-001" not in client.queries[0].statement
    assert client.queries[0].parameters[0].name == "store_id"
    assert store.store_id == "ST-001"
