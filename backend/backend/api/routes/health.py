from fastapi import APIRouter
from sqlalchemy import text

from backend.config import settings
from backend.db.session import engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "phantom-vsa-backend"}


@router.get("/health/db")
async def db_health() -> dict:
    async with engine.connect() as conn:
        await conn.execute(text("select 1"))
    return {
        "status": "ok",
        "database": "reachable",
        "app_env": settings.app_env,
        "auto_create_tables": settings.auto_create_tables,
    }


@router.get("/health/observability")
async def observability_health() -> dict:
    return {
        "status": "ok",
        "provider": settings.observability_provider,
        "trace_sample_rate": settings.trace_sample_rate,
        "structured_logger": "phantom.telemetry",
        "otel_service_name": settings.otel_service_name,
        "otlp_endpoint_configured": bool(settings.otel_exporter_otlp_endpoint),
        "otel_fail_closed": settings.otel_fail_closed,
    }
