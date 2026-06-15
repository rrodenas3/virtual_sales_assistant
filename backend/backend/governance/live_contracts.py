from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from backend.clients.sql import QueryStatement, SQLClient, param

ContractName = Literal["databricks_osa_alerts", "databricks_rgm_recommendations", "snowflake_store_master"]


@dataclass(frozen=True)
class LiveDataContract:
    name: ContractName
    source_system: str
    sample_query: QueryStatement
    required_columns: tuple[str, ...]
    normalized_score_columns: tuple[str, ...] = ()
    non_null_columns: tuple[str, ...] = ()
    enforce_territory_filter: bool = False
    enforce_rep_filter: bool = False
    requires_alert_business_key: bool = False


@dataclass(frozen=True)
class ContractValidationResult:
    name: str
    valid: bool
    row_count: int
    missing_columns: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)


def live_data_contracts(
    *,
    territory_code: str = "WEST-01",
    rep_id: str = "REP-001",
    store_id: str = "ST-001",
) -> dict[ContractName, LiveDataContract]:
    return {
        "databricks_osa_alerts": LiveDataContract(
            name="databricks_osa_alerts",
            source_system="databricks",
            sample_query=QueryStatement(
                statement="""
SELECT store_id, store_name, retailer_name, territory_code, rep_id, sku_id, sku_name, category,
       prediction_date, risk_score, is_phantom_inventory, root_cause_label, data_freshness_ts,
       prediction_source_row_id, model_version
FROM osa_oos_alerts
WHERE territory_code = :territory_code AND rep_id = :rep_id
LIMIT 50
""".strip(),
                parameters=(param("territory_code", territory_code), param("rep_id", rep_id)),
            ),
            required_columns=(
                "store_id",
                "store_name",
                "retailer_name",
                "territory_code",
                "rep_id",
                "sku_id",
                "sku_name",
                "category",
                "prediction_date",
                "risk_score",
                "is_phantom_inventory",
                "root_cause_label",
                "data_freshness_ts",
                "prediction_source_row_id",
                "model_version",
            ),
            normalized_score_columns=("risk_score",),
            non_null_columns=("territory_code", "rep_id", "data_freshness_ts", "store_id", "sku_id", "prediction_date"),
            enforce_territory_filter=True,
            enforce_rep_filter=True,
            requires_alert_business_key=True,
        ),
        "databricks_rgm_recommendations": LiveDataContract(
            name="databricks_rgm_recommendations",
            source_system="databricks",
            sample_query=QueryStatement(
                statement="""
SELECT store_id, territory_code, rep_id, recommendation_id, recommendation_type, sku_id, sku_name,
       title, rationale, expected_value_eur, confidence_score, data_freshness_ts, model_version
FROM rgm_recommendations
WHERE territory_code = :territory_code AND rep_id = :rep_id
LIMIT 50
""".strip(),
                parameters=(param("territory_code", territory_code), param("rep_id", rep_id)),
            ),
            required_columns=(
                "store_id",
                "territory_code",
                "rep_id",
                "recommendation_id",
                "recommendation_type",
                "sku_id",
                "sku_name",
                "title",
                "rationale",
                "expected_value_eur",
                "confidence_score",
                "data_freshness_ts",
                "model_version",
            ),
            normalized_score_columns=("confidence_score",),
            non_null_columns=("territory_code", "rep_id", "data_freshness_ts", "store_id", "recommendation_id"),
            enforce_territory_filter=True,
            enforce_rep_filter=True,
        ),
        "snowflake_store_master": LiveDataContract(
            name="snowflake_store_master",
            source_system="snowflake",
            sample_query=QueryStatement(
                statement="""
SELECT store_id, store_name, retailer_name, address, store_tier, territory_code, rep_id,
       last_visit_date, next_visit_date, units_sold_30d, revenue_30d, promo_compliance_rate,
       revenue_opportunity_score, oos_sku_count, data_freshness_ts
FROM store_master
WHERE territory_code = :territory_code AND rep_id = :rep_id AND store_id = :store_id
LIMIT 50
""".strip(),
                parameters=(param("territory_code", territory_code), param("rep_id", rep_id), param("store_id", store_id)),
            ),
            required_columns=(
                "store_id",
                "store_name",
                "retailer_name",
                "address",
                "store_tier",
                "territory_code",
                "rep_id",
                "last_visit_date",
                "next_visit_date",
                "units_sold_30d",
                "revenue_30d",
                "promo_compliance_rate",
                "revenue_opportunity_score",
                "oos_sku_count",
                "data_freshness_ts",
            ),
            normalized_score_columns=("promo_compliance_rate", "revenue_opportunity_score"),
            non_null_columns=("territory_code", "rep_id", "data_freshness_ts", "store_id"),
            enforce_territory_filter=True,
            enforce_rep_filter=True,
        ),
    }


def validate_contract_rows(
    contract: LiveDataContract,
    rows: list[dict[str, Any]],
    *,
    expected_territory_code: str | None = None,
    expected_rep_id: str | None = None,
) -> ContractValidationResult:
    columns = set().union(*(row.keys() for row in rows)) if rows else set()
    missing = [column for column in contract.required_columns if column not in columns]
    violations: list[str] = []
    if not rows:
        violations.append("sample query returned no rows")

    for idx, row in enumerate(rows):
        for column in contract.non_null_columns:
            if row.get(column) in {None, ""}:
                violations.append(f"row {idx} has null required value for {column}")
        for column in contract.normalized_score_columns:
            value = row.get(column)
            try:
                score = float(value)
            except (TypeError, ValueError):
                violations.append(f"row {idx} has non-numeric {column}")
                continue
            if score < 0 or score > 1:
                violations.append(f"row {idx} has {column} outside 0..1")
        if contract.enforce_territory_filter and expected_territory_code and row.get("territory_code") != expected_territory_code:
            violations.append(f"row {idx} crossed territory filter")
        if contract.enforce_rep_filter and expected_rep_id and row.get("rep_id") != expected_rep_id:
            violations.append(f"row {idx} crossed rep filter")
        if contract.requires_alert_business_key:
            _validate_alert_business_key(row, idx, violations)

    return ContractValidationResult(
        name=contract.name,
        valid=not missing and not violations,
        row_count=len(rows),
        missing_columns=missing,
        violations=violations,
    )


async def validate_contract_with_client(
    contract: LiveDataContract,
    client: SQLClient,
    *,
    expected_territory_code: str | None = None,
    expected_rep_id: str | None = None,
) -> ContractValidationResult:
    rows = await client.execute(contract.sample_query)
    return validate_contract_rows(
        contract,
        rows,
        expected_territory_code=expected_territory_code,
        expected_rep_id=expected_rep_id,
    )


def contract_manifest() -> dict[str, dict[str, object]]:
    return {
        name: {
            "source_system": contract.source_system,
            "required_columns": list(contract.required_columns),
            "normalized_score_columns": list(contract.normalized_score_columns),
            "non_null_columns": list(contract.non_null_columns),
            "enforce_territory_filter": contract.enforce_territory_filter,
            "enforce_rep_filter": contract.enforce_rep_filter,
            "requires_alert_business_key": contract.requires_alert_business_key,
        }
        for name, contract in live_data_contracts().items()
    }


def _validate_alert_business_key(row: dict[str, Any], row_index: int, violations: list[str]) -> None:
    required = ("store_id", "sku_id", "prediction_date")
    if any(row.get(column) in {None, ""} for column in required):
        violations.append(f"row {row_index} cannot build alert business key")
        return
    try:
        prediction_date = _date_text(row["prediction_date"])
    except ValueError as exc:
        violations.append(f"row {row_index} has invalid prediction_date: {exc}")
        return
    alert_id = f"{row['store_id']}:{row['sku_id']}:{prediction_date}"
    if row.get("alert_id") and row["alert_id"] != alert_id:
        violations.append(f"row {row_index} alert_id does not match stable business key")


def _date_text(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    text = str(value)
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(str(value)) from exc
    return text
