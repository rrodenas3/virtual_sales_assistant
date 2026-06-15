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
    observability_provider: Literal["structured", "otlp_http", "none"] = "structured"
    trace_sample_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    otel_service_name: str = "phantom-vsa-backend"
    otel_exporter_otlp_endpoint: str | None = None
    otel_fail_closed: bool = False
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
    discovery_memory_retention_policy: str | None = None
    discovery_memory_scopes: str | None = None
    live_data_contract_validated: bool = False
    live_data_contract_last_validation_at: str | None = None
    live_data_contract_validation_summary: str | None = None
    territory_timezone: str = "Europe/Paris"
    osa_source_system: str = "mock"
    osa_model_version: str = "mock-v1"
    osa_adapter: Literal["mock", "databricks"] = "mock"
    rgm_adapter: Literal["mock", "databricks"] = "mock"
    store_master_adapter: Literal["mock", "snowflake"] = "mock"
    crm_adapter: Literal["local", "external"] = "local"
    erp_adapter: Literal["sandbox", "external"] = "sandbox"
    shelf_image_adapter: Literal["mock", "external"] = "mock"
    crm_endpoint: str | None = None
    crm_token_ref: str | None = None
    erp_endpoint: str | None = None
    erp_token_ref: str | None = None
    shelf_image_endpoint: str | None = None
    shelf_image_token_ref: str | None = None
    shelf_image_timeout_seconds: float = 8.0
    audit_sink: Literal["postgres", "unity_catalog"] = "postgres"
    audit_dual_write_enabled: bool = False
    audit_dual_write_fail_closed: bool = True
    audit_unity_catalog_table: str = "phantom.audit.agent_actions"
    guardrail_provider: Literal["pattern", "external_classifier"] = "pattern"
    guardrail_classifier_endpoint: str | None = None
    guardrail_classifier_block_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    guardrail_classifier_timeout_seconds: float = 3.0
    guardrail_fail_closed: bool = True
    agent_graph_enabled: bool = False
    agent_run_enabled: bool = False
    memory_provider: Literal["none", "mem0"] = "none"
    mem0_token_ref: str | None = None
    mem0_endpoint: str = "https://api.mem0.ai/v1"
    mem0_timeout_seconds: float = 5.0
    offline_agent_provider: Literal["none", "hermes", "ollama"] = "none"
    offline_agent_enabled: bool = False
    offline_agent_kill_switch: bool = True
    offline_agent_min_device_ram_gb: float = 8.0
    offline_agent_max_latency_ms: int = 2500
    offline_agent_min_tool_accuracy: float = Field(default=0.95, ge=0.0, le=1.0)
    summary_provider: Literal["template", "anthropic"] = "template"
    llm_model_id: str = "grounded-template-v1"
    anthropic_token_ref: str | None = None
    anthropic_model: str = "claude-haiku-4-5"
    anthropic_timeout_seconds: float = 8.0
    anthropic_max_tokens: int = 600
    ai_demo_eval_validated: bool = False
    ai_demo_eval_last_validation_at: str | None = None
    ai_demo_eval_validation_summary: str | None = None
    summary_fail_open: bool = False
    databricks_host: str | None = None
    databricks_token: str | None = None
    databricks_sql_warehouse_id: str | None = None
    snowflake_account: str | None = None
    snowflake_user: str | None = None
    snowflake_token: str | None = None
    snowflake_warehouse: str | None = None
    snowflake_database: str | None = None
    snowflake_schema: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
