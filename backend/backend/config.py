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
    auth_mode: Literal["mock_jwt"] = "mock_jwt"
    auth_provider: Literal["mock", "external_jwt"] = "mock"
    external_jwt_issuer: str | None = None
    external_jwt_audience: str | None = None
    territory_timezone: str = "Europe/Paris"
    osa_source_system: str = "mock"
    osa_model_version: str = "mock-v1"
    llm_model_id: str = "grounded-template-v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
