from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.config import settings
from backend.governance.activation import runtime_validation_commands
from backend.governance.activation_evidence import build_evidence_manifest
from backend.services.summary_providers import summary_provider_status


def build_ai_demo_activation_pack() -> dict[str, Any]:
    summary_status = summary_provider_status()
    commands = runtime_validation_commands("ai-demo")
    command_names = {command["name"] for command in commands}
    required_commands = [
        command
        for command in commands
        if command["name"]
        in {
            "ai_summary_eval",
            "mlflow_handoff_dry_run",
            "ai_demo_eval_evidence",
            "summary_load_test",
            "ai_demo_readiness",
        }
    ]
    evidence_manifest = build_evidence_manifest("ai-demo")
    blockers = list(summary_status["ai_demo_blockers"])
    if not settings.agent_run_enabled:
        blockers.append("AGENT_RUN_ENABLED must be true for AI-demo readiness")

    config_checks = [
        {
            "name": "summary_provider",
            "ready": settings.summary_provider == "anthropic",
            "public_value": settings.summary_provider,
            "required_value": "anthropic",
            "notes": "Template mode proves scaffold safety only; AI-demo requires the approved provider.",
        },
        {
            "name": "anthropic_token_ref",
            "ready": bool(settings.anthropic_token_ref),
            "value_present": bool(settings.anthropic_token_ref),
            "notes": "Presence only; the token reference value is never returned or written to artifacts.",
        },
        {
            "name": "anthropic_model",
            "ready": bool(settings.anthropic_model),
            "public_value": settings.anthropic_model,
            "required_value": "claude-haiku-4-5",
            "notes": "Configurable, but pilot docs currently standardize on claude-haiku-4-5.",
        },
        {
            "name": "summary_fail_open",
            "ready": settings.summary_fail_open is False,
            "public_value": str(settings.summary_fail_open).lower(),
            "required_value": "false",
            "notes": "AI-demo should fail closed so template fallback cannot mask provider failure.",
        },
        {
            "name": "agent_run_enabled",
            "ready": settings.agent_run_enabled is True,
            "public_value": str(settings.agent_run_enabled).lower(),
            "required_value": "true",
            "notes": "AI-demo validates the SSE assistant path, not only the direct summary route.",
        },
        {
            "name": "ai_demo_eval_validated",
            "ready": bool(settings.ai_demo_eval_validated),
            "public_value": str(settings.ai_demo_eval_validated).lower(),
            "required_value": "true",
            "notes": "Set only after ai_demo_eval_evidence.py validates a provider=anthropic eval artifact.",
        },
    ]
    next_commands = [
        command
        for command in required_commands
        if command["name"] in command_names
    ]
    if summary_status["ai_demo_ready"] and settings.agent_run_enabled:
        next_actions = ["AI-demo gate is clear; proceed to live data contract readiness."]
    else:
        next_actions = list(summary_status["ai_demo_next_actions"])
        if not settings.agent_run_enabled:
            next_actions.append("Set AGENT_RUN_ENABLED=true in the approved AI-demo runtime")
        next_actions.append("Run the AI-demo activation pack again after recording AI_DEMO_EVAL_* evidence")

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "target": "ai-demo",
        "ready": not blockers,
        "stage": summary_status["ai_demo_stage"],
        "summary_provider": summary_status["selected_provider"],
        "summary_model_id": summary_status["active_model"],
        "provider_ready": summary_status["ai_demo_provider_ready"],
        "eval_validated": summary_status["ai_demo_eval_validated"],
        "last_validation_at": summary_status["ai_demo_eval_last_validation_at"],
        "validation_summary": summary_status["ai_demo_eval_validation_summary"],
        "blockers": blockers,
        "next_actions": next_actions,
        "config_checks": config_checks,
        "required_commands": next_commands,
        "required_artifacts": evidence_manifest["required_artifacts"],
        "required_env_keys": evidence_manifest["required_env_keys"],
        "public_safety_notes": [
            "Token references are reported only as value_present booleans.",
            "Generated artifacts must not contain API keys, bearer tokens, client hostnames, or personal data.",
            "Template-only eval success is not AI-demo readiness.",
        ],
    }
