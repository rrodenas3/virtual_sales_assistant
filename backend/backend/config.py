from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./phantom.db"
    app_env: Literal["local", "test", "production"] = "local"
    auto_create_tables: bool = True
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    observability_provider: Literal["structured", "none"] = "structured"
    trace_sample_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    auth_mode: Literal["mock_jwt"] = "mock_jwt"
    auth_provider: Literal["mock", "external_jwt"] = "mock"
    external_jwt_issuer: str | None = None
    external_jwt_audience: str | None = None
    external_jwt_jwks_url: str | None = None
    external_jwt_role_claim: str = "role"
    external_jwt_territory_claim: str = "territory_code"
    external_jwt_algorithms: list[str] = Field(default_factory=lambda: ["RS256"])
    discovery_data_sharing_model: str | None = None
    discovery_crm_platform: str | None = None
    discovery_erp_sandbox: str | None = None
    discovery_pilot_territory: str | None = "WEST-01"
    discovery_rep_device: str | None = "PWA"
    discovery_sso_provider: str | None = None
    discovery_data_residency: str | None = None
    discovery_offline_sync_policy: str | None = "browser-feedback-queue"
    territory_timezone: str = "Europe/Paris"
    osa_source_system: str = "mock"
    osa_model_version: str = "mock-v1"
    osa_adapter: Literal["mock", "databricks"] = "mock"
    rgm_adapter: Literal["mock", "databricks"] = "mock"
    store_master_adapter: Literal["mock", "snowflake"] = "mock"
    audit_sink: Literal["postgres", "unity_catalog"] = "postgres"
    audit_dual_write_enabled: bool = False
    audit_dual_write_fail_closed: bool = True
    guardrail_provider: Literal["pattern", "external_classifier"] = "pattern"
    guardrail_classifier_endpoint: str | None = None
    guardrail_fail_closed: bool = True
    agent_graph_enabled: bool = False
    agent_run_enabled: bool = False
    memory_provider: Literal["none", "mem0"] = "none"
    mem0_token_ref: str | None = None
    llm_model_id: str = "grounded-template-v1"
    databricks_host: str | None = None
    databricks_token: str | None = None
    databricks_sql_warehouse_id: str | None = None
    snowflake_account: str | None = None
    snowflake_user: str | None = None
    snowflake_warehouse: str | None = None
    snowflake_database: str | None = None
    snowflake_schema: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
