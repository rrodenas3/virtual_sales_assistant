from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.schemas import ActivationTargetReadiness, DiscoveryGateOut, IntegrationReadinessResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.auth.providers import auth_status
from backend.config import settings
from backend.governance.action_providers import action_provider_status
from backend.governance.data_platform import data_platform_status
from backend.governance.discovery import discovery_gates, readiness_blockers, selected_live_modes
from backend.governance.guardrails import guardrail_status
from backend.governance.offline_agent import offline_agent_status
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


def _provider_blockers(provider_readiness: dict[str, dict]) -> list[str]:
    blockers: list[str] = []
    for provider_name, status_body in provider_readiness.items():
        if provider_name == "offline_agent" and not status_body.get("enabled") and status_body.get("provider") == "none":
            continue
        if status_body.get("ready", True):
            continue
        for blocker in status_body.get("blockers", []):
            blockers.append(f"{provider_name}.{blocker}")
    return blockers


def _activation_targets(
    *,
    discovery_blockers: list[str],
    provider_blockers: list[str],
    provider_readiness: dict[str, dict],
    summary_status: dict,
) -> list[ActivationTargetReadiness]:
    local_blockers = [*discovery_blockers, *provider_blockers]
    ai_demo_blockers = [
        *local_blockers,
        *list(summary_status["ai_demo_blockers"]),
    ]
    if not settings.agent_run_enabled:
        ai_demo_blockers.append("AGENT_RUN_ENABLED must be true for AI-demo readiness")

    pilot_blockers = list(ai_demo_blockers)
    if not settings.live_data_contract_validated:
        pilot_blockers.append("Live data contracts must be validated for pilot readiness")
    if not selected_live_modes():
        pilot_blockers.append("At least one live integration mode must be selected for pilot readiness")
    audit_status = provider_readiness.get("audit", {})
    if not audit_status.get("unity_selected"):
        pilot_blockers.append("Unity Catalog audit sink or mirror must be selected for pilot readiness")

    return [
        ActivationTargetReadiness(
            target="local",
            ready=not local_blockers,
            description="Local scaffold with mock/default providers",
            blockers=local_blockers,
        ),
        ActivationTargetReadiness(
            target="ai-demo",
            ready=not ai_demo_blockers,
            description="Real summary provider validation with the SSE assistant enabled",
            blockers=ai_demo_blockers,
        ),
        ActivationTargetReadiness(
            target="pilot",
            ready=not pilot_blockers,
            description="Credentialed pilot with live contracts, live modes, and audit mirror",
            blockers=pilot_blockers,
        ),
    ]


@router.get("/readiness", response_model=IntegrationReadinessResponse)
async def integration_readiness(current_user: CurrentUser = Depends(get_current_user)) -> IntegrationReadinessResponse:
    if current_user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager or admin role required")
    blockers = readiness_blockers()
    summary_status = summary_provider_status()
    provider_readiness = _provider_readiness()
    provider_blockers = _provider_blockers(provider_readiness)
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
            )
            for gate in discovery_gates()
        ],
        view_contract_validated=settings.live_data_contract_validated,
        last_validation_at=settings.live_data_contract_last_validation_at,
        validation_summary=settings.live_data_contract_validation_summary,
        summary_provider=str(summary_status["selected_provider"]),
        summary_model_id=str(summary_status["active_model"]),
        ai_demo_ready=bool(summary_status["ai_demo_ready"]),
        ai_demo_blockers=list(summary_status["ai_demo_blockers"]),
        activation_targets=_activation_targets(
            discovery_blockers=blockers,
            provider_blockers=provider_blockers,
            provider_readiness=provider_readiness,
            summary_status=summary_status,
        ),
    )
