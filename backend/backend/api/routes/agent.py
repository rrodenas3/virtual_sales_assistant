import json
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.osa import OSADataPort
from backend.api.schemas import AgentRunRequest, OSASummaryRequest, OSASummaryResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.config import settings
from backend.db.session import get_db
from backend.deps import get_osa_adapter
from backend.services.agent_summary import SummaryGuardrailError, SummaryValidationError, create_osa_summary

router = APIRouter(prefix="/agent", tags=["agent"])


def _http_error_for_summary(exc: ValueError) -> HTTPException:
    if isinstance(exc, SummaryGuardrailError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, SummaryValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/osa-summary", response_model=OSASummaryResponse)
async def osa_summary(
    request: OSASummaryRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> OSASummaryResponse:
    try:
        return await create_osa_summary(db, osa, current_user, request)
    except ValueError as exc:
        raise _http_error_for_summary(exc) from exc


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


@router.post("/run")
async def agent_run(
    request: AgentRunRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
) -> StreamingResponse:
    if not settings.agent_run_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run endpoint is disabled")
    if request.intent != "osa_summary":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only osa_summary intent is supported")

    run_id = request.run_id or str(uuid4())
    summary_request = OSASummaryRequest(
        territory_code=request.territory_code,
        store_id=request.store_id,
        session_id=request.session_id,
        alert_ids=request.alert_ids,
    )
    try:
        summary = await create_osa_summary(db, osa, current_user, summary_request)
    except ValueError as exc:
        raise _http_error_for_summary(exc) from exc

    async def events() -> AsyncIterator[str]:
        yield _sse("run_started", {"run_id": run_id, "session_id": request.session_id, "intent": request.intent})
        yield _sse(
            "message",
            {
                "run_id": run_id,
                "role": "assistant",
                "content": summary.summary,
                "grounded_alert_ids": summary.grounded_alert_ids,
            },
        )
        yield _sse(
            "audit",
            {
                "run_id": run_id,
                "audit_event_id": summary.audit_event_id,
                "model_id": summary.model_id,
            },
        )
        yield _sse("run_completed", {"run_id": run_id, "session_id": request.session_id})

    return StreamingResponse(events(), media_type="text/event-stream")
