from __future__ import annotations

import pytest

from backend.governance.live_contracts import live_data_contracts, validate_contract_rows


def test_contract_manifest_contains_required_osa_columns() -> None:
    contract = live_data_contracts()["databricks_osa_alerts"]

    assert "risk_score" in contract.required_columns
    assert "territory_code" in contract.required_columns
    assert "rep_id" in contract.required_columns
    assert contract.requires_alert_business_key is True


def test_osa_contract_validates_normalized_scores_and_business_key() -> None:
    contract = live_data_contracts()["databricks_osa_alerts"]

    result = validate_contract_rows(
        contract,
        [
            {
                "store_id": "ST-001",
                "store_name": "West Market 01",
                "retailer_name": "Northstar Retail",
                "territory_code": "WEST-01",
                "rep_id": "REP-001",
                "sku_id": "SKU-4001",
                "sku_name": "Core SKU 4001",
                "category": "Beverages",
                "prediction_date": "2026-06-15",
                "risk_score": 0.91,
                "is_phantom_inventory": True,
                "root_cause_label": "phantom",
                "data_freshness_ts": "2026-06-15T00:00:00+00:00",
                "prediction_source_row_id": "PRED-1",
                "model_version": "model-v1",
            }
        ],
        expected_territory_code="WEST-01",
        expected_rep_id="REP-001",
    )

    assert result.valid is True
    assert result.missing_columns == []
    assert result.violations == []


def test_contract_validation_reports_missing_columns_and_filter_leakage() -> None:
    contract = live_data_contracts()["snowflake_store_master"]

    result = validate_contract_rows(
        contract,
        [
            {
                "store_id": "ST-001",
                "store_name": "West Market 01",
                "retailer_name": "Northstar Retail",
                "address": "101 Commerce Ave",
                "store_tier": "A",
                "territory_code": "EAST-01",
                "rep_id": "REP-999",
                "units_sold_30d": 1200,
                "revenue_30d": 24000,
                "promo_compliance_rate": 1.2,
                "revenue_opportunity_score": 0.75,
                "oos_sku_count": 5,
                "data_freshness_ts": None,
            }
        ],
        expected_territory_code="WEST-01",
        expected_rep_id="REP-001",
    )

    assert result.valid is False
    assert "next_visit_date" in result.missing_columns
    assert "last_visit_date" in result.missing_columns
    assert any("promo_compliance_rate outside 0..1" in violation for violation in result.violations)
    assert any("crossed territory filter" in violation for violation in result.violations)
    assert any("crossed rep filter" in violation for violation in result.violations)
    assert any("data_freshness_ts" in violation for violation in result.violations)


def test_osa_contract_rejects_mismatched_alert_id() -> None:
    contract = live_data_contracts()["databricks_osa_alerts"]

    result = validate_contract_rows(
        contract,
        [
            {
                "alert_id": "ST-001:SKU-4001:2026-06-14",
                "store_id": "ST-001",
                "store_name": "West Market 01",
                "retailer_name": "Northstar Retail",
                "territory_code": "WEST-01",
                "rep_id": "REP-001",
                "sku_id": "SKU-4001",
                "sku_name": "Core SKU 4001",
                "category": "Beverages",
                "prediction_date": "2026-06-15",
                "risk_score": 0.91,
                "is_phantom_inventory": True,
                "root_cause_label": "phantom",
                "data_freshness_ts": "2026-06-15T00:00:00+00:00",
                "prediction_source_row_id": "PRED-1",
                "model_version": "model-v1",
            }
        ],
        expected_territory_code="WEST-01",
        expected_rep_id="REP-001",
    )

    assert result.valid is False
    assert any("stable business key" in violation for violation in result.violations)


@pytest.mark.asyncio
async def test_contract_sample_queries_keep_filters_parameterized() -> None:
    contracts = live_data_contracts(territory_code="WEST-01", rep_id="REP-001", store_id="ST-001")

    for contract in contracts.values():
        assert "WEST-01" not in contract.sample_query.statement
        assert "REP-001" not in contract.sample_query.statement
        assert {param.name for param in contract.sample_query.parameters} >= {"territory_code", "rep_id"}
