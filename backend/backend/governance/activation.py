from __future__ import annotations

from typing import Any, Literal, TypedDict

from backend.config import settings
from backend.governance.discovery import selected_live_modes

ActivationTargetName = Literal["local", "ai-demo", "pilot"]


class ActivationTarget(TypedDict):
    target: ActivationTargetName
    ready: bool
    description: str
    blockers: list[str]


def flatten_provider_blockers(provider_readiness: dict[str, dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for provider_name, status_body in provider_readiness.items():
        if provider_name == "offline_agent" and not status_body.get("enabled") and status_body.get("provider") == "none":
            continue
        if status_body.get("ready", True):
            continue
        for blocker in status_body.get("blockers", []):
            blockers.append(f"{provider_name}.{blocker}")
    return blockers


def build_activation_targets(
    *,
    discovery_blockers: list[str],
    provider_blockers: list[str],
    provider_readiness: dict[str, dict[str, Any]],
    summary_status: dict[str, Any],
) -> list[ActivationTarget]:
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
        {
            "target": "local",
            "ready": not local_blockers,
            "description": "Local scaffold with mock/default providers",
            "blockers": local_blockers,
        },
        {
            "target": "ai-demo",
            "ready": not ai_demo_blockers,
            "description": "Real summary provider validation with the SSE assistant enabled",
            "blockers": ai_demo_blockers,
        },
        {
            "target": "pilot",
            "ready": not pilot_blockers,
            "description": "Credentialed pilot with live contracts, live modes, and audit mirror",
            "blockers": pilot_blockers,
        },
    ]
