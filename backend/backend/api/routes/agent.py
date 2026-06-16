import json
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.adapters.crm import CRMPort
from backend.adapters.osa import OSADataPort
from backend.api.schemas import (
    AgentRunRequest,
    CreateManagerTaskRequest,
    CreateOrderDraftRequest,
    OSASummaryRequest,
    OSASummaryResponse,
    VisitLogDraftRequest,
)
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.config import settings
from backend.db.session import get_db
from backend.deps import get_crm_adapter, get_osa_adapter
from backend.services.agent_actions import (
    AgentActionConflict,
    AgentActionForbidden,
    AgentActionNotFound,
    create_manager_task_action,
    create_order_draft_action,
    create_visit_log_draft_action,
)
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
    return f"event: {event}\ndata: {json.dumps(jsonable_encoder(data), separators=(',', ':'))}\n\n"


def _bad_action_payload(exc: ValidationError) -> HTTPException:
    return HTTPException(status_code=422, detail=exc.errors())


def _http_error_for_action(exc: ValueError) -> HTTPException:
    if isinstance(exc, AgentActionForbidden):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, AgentActionNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, AgentActionConflict):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/run")
async def agent_run(
    request: AgentRunRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    osa: OSADataPort = Depends(get_osa_adapter),
    crm: CRMPort = Depends(get_crm_adapter),
) -> StreamingResponse:
    if not settings.agent_run_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run endpoint is disabled")

    run_id = request.run_id or str(uuid4())

    supervisor_decision = {
        "run_id": run_id,
        "intent": request.intent,
        "agent": "osa_agent" if request.intent == "osa_summary" else "action_agent",
        "requires_human_approval": request.intent == "order_draft",
    }

    action_result: dict
    audit_event_id: str | None = None
    model_id: str | None = None
    if request.intent == "osa_summary":
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
        audit_event_id = summary.audit_event_id
        model_id = summary.model_id
        action_result = {
            "type": "osa_summary",
            "summary": summary.summary,
            "grounded_alert_ids": summary.grounded_alert_ids,
            "model_id": summary.model_id,
            "audit_event_id": summary.audit_event_id,
        }
    elif request.intent == "order_draft":
        try:
            draft_request = CreateOrderDraftRequest(
                store_id=request.store_id,
                session_id=request.session_id,
                items=request.items,
                notes=request.notes,
            )
        except ValidationError as exc:
            raise _bad_action_payload(exc) from exc
        try:
            draft = await create_order_draft_action(db, osa, current_user, draft_request)
        except ValueError as exc:
            raise _http_error_for_action(exc) from exc
        audit_event_id = draft.audit_event_id
        action_result = {
            "type": "order_draft",
            "draft": draft.model_dump(mode="json"),
            "hitl": {
                "required": True,
                "reason": "order_submit_requires_human_approval",
                "resume_token": f"{request.session_id}:hitl:order:{draft.draft_id}",
            },
        }
    elif request.intent == "visit_log_draft":
        try:
            visit_request = VisitLogDraftRequest(
                store_id=request.store_id,
                session_id=request.session_id,
                notes=request.notes,
                outcome=request.outcome,
            )
        except ValidationError as exc:
            raise _bad_action_payload(exc) from exc
        try:
            visit = await create_visit_log_draft_action(db, osa, crm, current_user, visit_request)
        except ValueError as exc:
            raise _http_error_for_action(exc) from exc
        audit_event_id = visit.audit_event_id
        action_result = {
            "type": "visit_log_draft",
            "visit_log": visit.model_dump(mode="json"),
        }
    else:
        try:
            task_request = CreateManagerTaskRequest(
                territory_code=request.territory_code,
                store_id=request.store_id,
                assigned_rep_id=request.assigned_rep_id,
                session_id=request.session_id,
                title=request.title,
                task_type=request.task_type,
                priority=request.priority,
                due_date=request.due_date,
                notes=request.notes,
                linked_alert_ids=request.alert_ids or [],
            )
        except ValidationError as exc:
            raise _bad_action_payload(exc) from exc
        try:
            task = await create_manager_task_action(db, osa, current_user, task_request)
        except ValueError as exc:
            raise _http_error_for_action(exc) from exc
        audit_event_id = task.audit_event_id
        action_result = {
            "type": "manager_task",
            "task": task.model_dump(mode="json"),
        }

    async def events() -> AsyncIterator[str]:
        yield _sse("run_started", {"run_id": run_id, "session_id": request.session_id, "intent": request.intent})
        yield _sse("supervisor_decision", supervisor_decision)
        if request.intent == "osa_summary":
            yield _sse(
                "message",
                {
                    "run_id": run_id,
                    "role": "assistant",
                    "content": action_result["summary"],
                    "grounded_alert_ids": action_result["grounded_alert_ids"],
                },
            )
        else:
            yield _sse("action_result", {"run_id": run_id, **action_result})
        if action_result.get("hitl"):
            yield _sse("hitl_required", {"run_id": run_id, **action_result["hitl"]})
        if audit_event_id:
            yield _sse("audit", {"run_id": run_id, "audit_event_id": audit_event_id, "model_id": model_id})
        yield _sse("run_completed", {"run_id": run_id, "session_id": request.session_id})

    return StreamingResponse(events(), media_type="text/event-stream")
