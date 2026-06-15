from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes import admin, agent, alerts, approvals, audit, crm, health, integrations, manager, metrics, orders, rgm, shelf_images, stores, sync, visits
from backend.config import settings
from backend.db.models import Base
from backend.db.session import engine
from backend.services.telemetry import log_structured_event, perf_counter_ms, should_sample_trace


def should_auto_create_tables() -> bool:
    return settings.auto_create_tables and settings.app_env in {"local", "test"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if should_auto_create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="PHANTOM VSA Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    started_ms = perf_counter_ms()
    sampled = should_sample_trace()
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        duration_ms = round(perf_counter_ms() - started_ms, 2)
        if sampled:
            log_structured_event(
                "http_request",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
            )
        return JSONResponse(
            status_code=500,
            content={"code": "internal_error", "message": str(exc), "request_id": request_id},
        )
    response.headers["x-request-id"] = request_id
    duration_ms = round(perf_counter_ms() - started_ms, 2)
    response.headers["x-response-time-ms"] = str(duration_ms)
    if sampled:
        log_structured_event(
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": "http_error", "message": str(exc.detail), "request_id": request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    return JSONResponse(
        status_code=422,
        content={"code": "validation_error", "message": str(exc), "request_id": request_id},
    )


for router in [
    health.router,
    integrations.router,
    metrics.router,
    manager.router,
    admin.router,
    visits.router,
    stores.router,
    rgm.router,
    shelf_images.router,
    alerts.router,
    orders.router,
    approvals.router,
    crm.router,
    sync.router,
    agent.router,
    audit.router,
]:
    app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root() -> dict:
    return {
        "service": "PHANTOM VSA Backend",
        "status": "ok",
        "api_base": "/api/v1",
        "health": "/api/v1/health",
        "docs": "/docs",
        "frontend": "http://localhost:5173",
    }


@app.get("/api/v1")
async def api_index() -> dict:
    return {
        "service": "PHANTOM VSA API",
        "routes": [
            "GET /api/v1/health",
            "GET /api/v1/health/observability",
            "GET /api/v1/health/db",
            "GET /api/v1/health/ai",
            "GET /api/v1/health/offline-agent",
            "GET /api/v1/health/guardrails",
            "GET /api/v1/health/memory",
            "GET /api/v1/integrations/readiness",
            "GET /api/v1/metrics/pilot",
            "GET /api/v1/manager/territory-summary?territory_code=WEST-01",
            "GET /api/v1/manager/approval-queue?territory_code=WEST-01",
            "POST /api/v1/manager/tasks",
            "GET /api/v1/manager/tasks?territory_code=WEST-01",
            "GET /api/v1/manager/my-tasks",
            "POST /api/v1/manager/tasks/{task_id}/status",
            "GET /api/v1/admin/audit-events?limit=75",
            "GET /api/v1/admin/audit-events/{event_id}",
            "GET /api/v1/visits/today?territory_code=WEST-01",
            "GET /api/v1/stores/{store_id}",
            "GET /api/v1/stores/{store_id}/alerts",
            "GET /api/v1/stores/{store_id}/rgm-recommendations",
            "POST /api/v1/stores/{store_id}/shelf-image-analysis",
            "POST /api/v1/alerts/{alert_id}/feedback",
            "POST /api/v1/orders/drafts",
            "GET /api/v1/orders/drafts/{draft_id}",
            "POST /api/v1/approvals/{draft_id}/approve",
            "POST /api/v1/approvals/{draft_id}/reject",
            "POST /api/v1/orders/drafts/{draft_id}/submit-sandbox",
            "POST /api/v1/crm/visit-log-drafts",
            "POST /api/v1/sync/feedback-events",
            "POST /api/v1/agent/osa-summary",
            "POST /api/v1/agent/run",
            "GET /api/v1/audit/session/{session_id}",
        ],
    }
