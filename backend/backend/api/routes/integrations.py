from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.schemas import DiscoveryGateOut, IntegrationReadinessResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.auth.providers import auth_status
from backend.config import settings
from backend.governance.activation import build_activation_targets, flatten_provider_blockers
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
        ai_demo_blockers=list(summary_status["ai_demo_blockers"]),
        activation_targets=build_activation_targets(
            discovery_blockers=blockers,
            provider_blockers=provider_blockers,
            provider_readiness=provider_readiness,
            summary_status=summary_status,
        ),
    )
