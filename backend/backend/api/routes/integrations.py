from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.schemas import DiscoveryGateOut, IntegrationReadinessResponse
from backend.auth.mock_jwt import CurrentUser, get_current_user
from backend.governance.discovery import discovery_gates, readiness_blockers, selected_live_modes

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/readiness", response_model=IntegrationReadinessResponse)
async def integration_readiness(current_user: CurrentUser = Depends(get_current_user)) -> IntegrationReadinessResponse:
    if current_user.role not in {"manager", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager or admin role required")
    blockers = readiness_blockers()
    return IntegrationReadinessResponse(
        ready=not blockers,
        selected_live_modes=sorted(selected_live_modes()),
        blockers=blockers,
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
    )
