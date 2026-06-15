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


class RuntimeValidationCommand(TypedDict):
    name: str
    command: str
    notes: str


def runtime_validation_commands(target: ActivationTargetName) -> list[RuntimeValidationCommand]:
    commands: list[RuntimeValidationCommand] = [
        {
            "name": "public_safety_scan",
            "command": "bash ./scripts/public_safety_scan.sh",
            "notes": "Required before sharing or publishing artifacts.",
        },
        {
            "name": "local_readiness",
            "command": "python scripts/pilot_readiness_report.py --target local --output-dir artifacts/readiness/local",
            "notes": "Safe local scaffold gate using mock/default providers.",
        },
        {
            "name": "api_contract",
            "command": "python scripts/validate_api_contract.py --base-url http://localhost:8000 --output-dir artifacts/api-contract",
            "notes": "Detects stale backend processes missing current manager/readiness routes.",
        },
        {
            "name": "final_api_smoke",
            "command": "python scripts/final_api_smoke.py --output-dir artifacts/final-api-smoke",
            "notes": "End-to-end local API smoke covering rep, manager, admin, HITL, audit, and metrics paths.",
        },
    ]
    if target in {"ai-demo", "pilot"}:
        commands.extend(
            [
                {
                    "name": "ai_summary_eval",
                    "command": "python scripts/run_eval.py --require-provider anthropic --output-dir artifacts/eval-ai",
                    "notes": "Must pass with the configured approved provider before claiming AI-assistant behavior.",
                },
                {
                    "name": "mlflow_handoff_dry_run",
                    "command": (
                        "python scripts/log_eval_to_mlflow.py --artifact-dir artifacts/eval-ai "
                        "--experiment-name phantom-vsa-evals --dry-run --output-dir artifacts/eval-ai"
                    ),
                    "notes": "Validates eval artifacts and produces local handoff manifests without a tracking server.",
                },
                {
                    "name": "ai_demo_eval_evidence",
                    "command": (
                        "python scripts/ai_demo_eval_evidence.py --artifact-dir artifacts/eval-ai "
                        "--output-dir artifacts/eval-ai"
                    ),
                    "notes": "Writes the exact AI_DEMO_EVAL_* values to record after the approved eval passes.",
                },
                {
                    "name": "ai_demo_readiness",
                    "command": "python scripts/pilot_readiness_report.py --target ai-demo --output-dir artifacts/readiness/ai-demo",
                    "notes": "Requires approved summary provider configuration.",
                },
                {
                    "name": "summary_load_test",
                    "command": (
                        "python scripts/load_test.py --base-url http://localhost:8000 --requests 50 "
                        "--concurrency 10 --threshold-p95-ms 5000 --output-dir artifacts/load/summary"
                    ),
                    "notes": (
                        "Set LOAD_TEST_BEARER_TOKEN only in the approved runtime environment when validating "
                        "external identity."
                    ),
                },
            ]
        )
    if target == "pilot":
        commands.extend(
            [
                {
                    "name": "live_data_contracts",
                    "command": "python scripts/validate_live_data_contracts.py --output-dir artifacts/contracts/live",
                    "notes": "Run only in an approved credentialed environment.",
                },
                {
                    "name": "unity_audit_smoke",
                    "command": "python scripts/unity_audit_smoke.py --output-dir artifacts/unity-audit-smoke",
                    "notes": "Dry-run parameterized audit insert and DDL drift check before credentialed Unity Catalog smoke.",
                },
                {
                    "name": "pilot_env_handoff",
                    "command": (
                        "python scripts/pilot_env_handoff.py --ai-demo-env artifacts/eval-ai/ai_demo_eval_env.json "
                        "--live-data-env artifacts/contracts/live/readiness_env.json --output-dir artifacts/pilot-env"
                    ),
                    "notes": "Merges non-secret AI-demo and live-data validation env values for final pilot runtime setup.",
                },
                {
                    "name": "pilot_readiness",
                    "command": "python scripts/pilot_readiness_report.py --target pilot --output-dir artifacts/readiness/pilot",
                    "notes": (
                        "Final gate after AI-demo, live data, identity, audit, action provider, memory, and "
                        "offline decisions are approved."
                    ),
                },
            ]
        )
    return commands


def runtime_validation_command_sets() -> dict[ActivationTargetName, list[RuntimeValidationCommand]]:
    return {
        "local": runtime_validation_commands("local"),
        "ai-demo": runtime_validation_commands("ai-demo"),
        "pilot": runtime_validation_commands("pilot"),
    }


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
