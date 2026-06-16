from fastapi import APIRouter, Depends, HTTPException, status

from typing import Literal

from backend.api.schemas import (
    AIDemoActivationPackResponse,
    ActivationRunbookResponse,
    DiscoveryGateOut,
    DiscoveryPacketResponse,
    IntegrationReadinessResponse,
    PilotGapReportResponse,
)
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.auth.providers import auth_status
from backend.config import settings
from backend.governance.activation import build_activation_targets, flatten_provider_blockers, runtime_validation_command_sets
from backend.governance.activation_evidence import build_evidence_manifest_sets
from backend.governance.activation_runbook import build_activation_runbook
from backend.governance.ai_demo_activation import build_ai_demo_activation_pack
from backend.governance.action_providers import action_provider_status
from backend.governance.data_platform import data_platform_status
from backend.governance.discovery_packet import build_discovery_packet
from backend.governance.discovery import discovery_gates, readiness_blockers, selected_live_modes
from backend.governance.guardrails import guardrail_status
from backend.governance.offline_agent import offline_agent_status
from backend.governance.pilot_gaps import build_gap_report
from backend.governance.shelf_image import shelf_image_status
from backend.memory.adapters import memory_status
from backend.services.audit_sinks import audit_sink_status
from backend.services.summary_providers import summary_provider_status
from backend.services.telemetry import observability_status

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _provider_readiness() -> dict[str, dict]:
    return {
        "auth": auth_status(),
        "data_platform": data_platform_status(),
        "action_providers": action_provider_status(),
        "shelf_image": shelf_image_status(),
        "memory": memory_status(),
        "audit": audit_sink_status(),
        "guardrails": guardrail_status(),
        "offline_agent": offline_agent_status(),
        "observability": observability_status(),
    }


def _activation_context() -> tuple[list[dict], dict[str, dict], dict]:
    blockers = readiness_blockers()
    summary_status = summary_provider_status()
    provider_readiness = _provider_readiness()
    activation_targets = build_activation_targets(
        discovery_blockers=blockers,
        provider_blockers=flatten_provider_blockers(provider_readiness),
        provider_readiness=provider_readiness,
        summary_status=summary_status,
    )
    return activation_targets, provider_readiness, summary_status


@router.get("/readiness", response_model=IntegrationReadinessResponse)
async def integration_readiness(current_user: CurrentUser = Depends(get_current_user)) -> IntegrationReadinessResponse:
    if current_user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager or admin role required")
    blockers = readiness_blockers()
    summary_status = summary_provider_status()
    provider_readiness = _provider_readiness()
    provider_blockers = flatten_provider_blockers(provider_readiness)
    return IntegrationReadinessResponse(
        ready=not blockers and not provider_blockers,
        selected_live_modes=sorted(selected_live_modes()),
        blockers=blockers,
        provider_blockers=provider_blockers,
        provider_readiness=provider_readiness,
        gates=[
            DiscoveryGateOut(
                topic=gate.topic,
                setting_name=gate.setting_name,
                status=gate.status,
                value=gate.value,
                required_for=list(gate.required_for),
                notes=gate.notes,
                owner=gate.owner,
            )
            for gate in discovery_gates()
        ],
        view_contract_validated=settings.live_data_contract_validated,
        last_validation_at=settings.live_data_contract_last_validation_at,
        validation_summary=settings.live_data_contract_validation_summary,
        summary_provider=str(summary_status["selected_provider"]),
        summary_model_id=str(summary_status["active_model"]),
        ai_demo_ready=bool(summary_status["ai_demo_ready"]),
        ai_demo_provider_ready=bool(summary_status["ai_demo_provider_ready"]),
        ai_demo_eval_validated=bool(summary_status["ai_demo_eval_validated"]),
        ai_demo_eval_last_validation_at=summary_status["ai_demo_eval_last_validation_at"],
        ai_demo_eval_validation_summary=summary_status["ai_demo_eval_validation_summary"],
        ai_demo_stage=str(summary_status["ai_demo_stage"]),
        ai_demo_blockers=list(summary_status["ai_demo_blockers"]),
        ai_demo_next_actions=list(summary_status["ai_demo_next_actions"]),
        ai_demo_validation_command=str(summary_status["ai_demo_validation_command"]),
        activation_targets=build_activation_targets(
            discovery_blockers=blockers,
            provider_blockers=provider_blockers,
            provider_readiness=provider_readiness,
            summary_status=summary_status,
        ),
        runtime_validation_commands=runtime_validation_command_sets(),
        activation_evidence_manifests=build_evidence_manifest_sets(),
    )


@router.get("/pilot-gap-report", response_model=PilotGapReportResponse)
async def pilot_gap_report(
    target: Literal["local", "ai-demo", "pilot"] = "local",
    current_user: CurrentUser = Depends(get_current_user),
) -> PilotGapReportResponse:
    if current_user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager or admin role required")
    activation_targets, _, _ = _activation_context()
    return PilotGapReportResponse(**build_gap_report(target, [dict(item) for item in activation_targets]))


@router.get("/activation-runbook", response_model=ActivationRunbookResponse)
async def activation_runbook(
    target: Literal["local", "ai-demo", "pilot"] = "pilot",
    current_user: CurrentUser = Depends(get_current_user),
) -> ActivationRunbookResponse:
    if current_user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager or admin role required")
    activation_targets, provider_readiness, _ = _activation_context()
    return ActivationRunbookResponse(
        **build_activation_runbook(
            current_target=target,
            activation_targets=[dict(item) for item in activation_targets],
            provider_readiness=provider_readiness,
            runtime_validation_commands=runtime_validation_command_sets(),
        )
    )


@router.get("/discovery-packet", response_model=DiscoveryPacketResponse)
async def discovery_packet(
    target: Literal["local", "ai-demo", "pilot"] = "pilot",
    current_user: CurrentUser = Depends(get_current_user),
) -> DiscoveryPacketResponse:
    if current_user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager or admin role required")
    return DiscoveryPacketResponse(**build_discovery_packet(target))


@router.get("/ai-demo-activation-pack", response_model=AIDemoActivationPackResponse)
async def ai_demo_activation_pack(
    current_user: CurrentUser = Depends(get_current_user),
) -> AIDemoActivationPackResponse:
    if current_user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager or admin role required")
    return AIDemoActivationPackResponse(**build_ai_demo_activation_pack())
