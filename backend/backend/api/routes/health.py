from fastapi import APIRouter
from sqlalchemy import text

from backend.auth.providers import auth_status
from backend.config import settings
from backend.db.session import engine
from backend.governance.action_providers import action_provider_status
from backend.governance.data_platform import data_platform_status
from backend.governance.guardrails import guardrail_status
from backend.governance.offline_agent import offline_agent_status
from backend.governance.shelf_image import shelf_image_status
from backend.memory.adapters import memory_status
from backend.services.audit_sinks import audit_sink_status
from backend.services.summary_providers import summary_provider_status

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


@router.get("/health/ai")
async def ai_health() -> dict:
    return {"status": "ok", **summary_provider_status()}


@router.get("/health/offline-agent")
async def offline_agent_health() -> dict:
    return {"status": "ok", **offline_agent_status()}


@router.get("/health/guardrails")
async def guardrails_health() -> dict:
    return {"status": "ok", **guardrail_status()}


@router.get("/health/memory")
async def memory_health() -> dict:
    return {"status": "ok", **memory_status()}


@router.get("/health/action-providers")
async def action_providers_health() -> dict:
    return {"status": "ok", **action_provider_status()}


@router.get("/health/data-platform")
async def data_platform_health() -> dict:
    return {"status": "ok", **data_platform_status()}


@router.get("/health/auth")
async def auth_health() -> dict:
    return {"status": "ok", **auth_status()}


@router.get("/health/shelf-image")
async def shelf_image_health() -> dict:
    return {"status": "ok", **shelf_image_status()}


@router.get("/health/audit-sink")
async def audit_sink_health() -> dict:
    return {"status": "ok", **audit_sink_status()}
