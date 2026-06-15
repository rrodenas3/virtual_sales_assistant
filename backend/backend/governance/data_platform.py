from __future__ import annotations

from backend.config import Settings, settings


def _databricks_selected(config: Settings) -> bool:
    return config.osa_adapter == "databricks" or config.rgm_adapter == "databricks"


def _snowflake_selected(config: Settings) -> bool:
    return config.store_master_adapter == "snowflake"


def _databricks_status(config: Settings) -> dict:
    selected = _databricks_selected(config)
    blockers: list[str] = []
    if selected:
        for name in ("databricks_host", "databricks_token", "databricks_sql_warehouse_id"):
            if not getattr(config, name):
                blockers.append(name)
        if not config.discovery_data_sharing_model:
            blockers.append("discovery_data_sharing_model")
        if not config.discovery_data_residency:
            blockers.append("discovery_data_residency")
        if not config.live_data_contract_validated:
            blockers.append("live_data_contract_validated")

    return {
        "selected": selected,
        "osa_adapter": config.osa_adapter,
        "rgm_adapter": config.rgm_adapter,
        "host_configured": bool(config.databricks_host),
        "token_configured": bool(config.databricks_token),
        "warehouse_configured": bool(config.databricks_sql_warehouse_id),
        "discovery_configured": bool(config.discovery_data_sharing_model and config.discovery_data_residency),
        "contract_validated": config.live_data_contract_validated,
        "ready": not blockers,
        "blockers": blockers,
    }


def _snowflake_status(config: Settings) -> dict:
    selected = _snowflake_selected(config)
    blockers: list[str] = []
    if selected:
        for name in (
            "snowflake_account",
            "snowflake_user",
            "snowflake_token",
            "snowflake_warehouse",
            "snowflake_database",
            "snowflake_schema",
        ):
            if not getattr(config, name):
                blockers.append(name)
        if not config.discovery_data_sharing_model:
            blockers.append("discovery_data_sharing_model")
        if not config.discovery_data_residency:
            blockers.append("discovery_data_residency")
        if not config.live_data_contract_validated:
            blockers.append("live_data_contract_validated")

    return {
        "selected": selected,
        "store_master_adapter": config.store_master_adapter,
        "account_configured": bool(config.snowflake_account),
        "user_configured": bool(config.snowflake_user),
        "token_configured": bool(config.snowflake_token),
        "warehouse_configured": bool(config.snowflake_warehouse),
        "database_configured": bool(config.snowflake_database),
        "schema_configured": bool(config.snowflake_schema),
        "discovery_configured": bool(config.discovery_data_sharing_model and config.discovery_data_residency),
        "contract_validated": config.live_data_contract_validated,
        "ready": not blockers,
        "blockers": blockers,
    }


def data_platform_status(config: Settings = settings) -> dict:
    databricks = _databricks_status(config)
    snowflake = _snowflake_status(config)
    return {
        "ready": databricks["ready"] and snowflake["ready"],
        "databricks": databricks,
        "snowflake": snowflake,
        "blockers": [f"databricks.{blocker}" for blocker in databricks["blockers"]]
        + [f"snowflake.{blocker}" for blocker in snowflake["blockers"]],
    }
