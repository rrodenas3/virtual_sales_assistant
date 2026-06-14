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
