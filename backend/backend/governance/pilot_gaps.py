from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from backend.governance.activation import runtime_validation_command_sets

Target = Literal["local", "ai-demo", "pilot"]

ROADMAP_ITEMS: list[dict[str, str]] = [
    {
        "area": "live_data",
        "owner": "delivery+engineering",
        "status": "blocked_by_credentials",
        "next_gate": "live_data_contracts",
    },
    {
        "area": "ai_demo",
        "owner": "engineering",
        "status": "blocked_by_approved_provider_runtime",
        "next_gate": "ai_summary_eval",
    },
    {
        "area": "fastmcp_transport",
        "owner": "engineering",
        "status": "deferred_until_runtime_requirements_are_known",
        "next_gate": "mcp_smoke",
    },
    {
        "area": "crm_erp_writeback",
        "owner": "delivery+engineering",
        "status": "blocked_by_client_discovery_and_sandbox_credentials",
        "next_gate": "action_provider_smoke",
    },
    {
        "area": "unity_catalog_audit",
        "owner": "delivery+engineering",
        "status": "blocked_by_databricks_credentials_and_table_approval",
        "next_gate": "unity_audit_smoke",
    },
    {
        "area": "mem0_memory",
        "owner": "delivery+engineering",
        "status": "blocked_by_workspace_retention_and_token_approval",
        "next_gate": "memory_provider_smoke",
    },
    {
        "area": "offline_local_agent",
        "owner": "engineering",
        "status": "deferred_until_device_ram_latency_and_tool_accuracy_spike",
        "next_gate": "offline_agent_health",
    },
]


def build_gap_report(target: Target, activation_targets: list[dict[str, Any]]) -> dict[str, Any]:
    command_sets = runtime_validation_command_sets()
    requested_target = next(item for item in activation_targets if item["target"] == target)
    gaps = [
        _gap_for_blocker(str(target_body["target"]), str(blocker), command_sets)
        for target_body in activation_targets
        if not target_body["ready"]
        for blocker in target_body["blockers"]
    ]
    command_names = _unique_command_names(gaps)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "target": target,
        "ready_for_requested_target": requested_target["ready"],
        "requested_target_blocker_count": len(requested_target["blockers"]),
        "gap_count": len(gaps),
        "activation_targets": [
            {
                "target": item["target"],
                "ready": item["ready"],
                "blocker_count": len(item["blockers"]),
                "blockers": item["blockers"],
            }
            for item in activation_targets
        ],
        "blocking_gaps": gaps,
        "recommended_commands": _commands_by_name(command_sets, command_names),
        "roadmap_items": ROADMAP_ITEMS,
        "public_safety_notes": [
            "No secrets, token values, local user paths, or client-confidential identifiers are included.",
            "Credentialed commands must run only in an approved runtime; reports store status and non-secret evidence only.",
        ],
    }


def _gap_for_blocker(
    target: str,
    blocker: str,
    command_sets: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    command_names = _command_names_for_blocker(blocker)
    return {
        "target": target,
        "blocker": blocker,
        "owner": _owner_for_blocker(blocker),
        "recommended_command_names": [name for name in command_names if _has_command(command_sets, name)],
    }


def _owner_for_blocker(blocker: str) -> str:
    text = blocker.lower()
    if any(term in text for term in ["summary_provider", "anthropic", "agent_run", "ai-demo"]):
        return "engineering"
    if any(term in text for term in ["live data", "unity catalog", "live integration", "credentials"]):
        return "delivery+engineering"
    return "shared"


def _command_names_for_blocker(blocker: str) -> list[str]:
    text = blocker.lower()
    if any(term in text for term in ["summary_provider", "anthropic", "ai-demo", "agent_run"]):
        return ["ai_summary_eval", "ai_demo_eval_evidence", "ai_demo_readiness", "summary_load_test"]
    if "live data" in text:
        return ["live_data_contracts", "pilot_env_handoff", "pilot_readiness"]
    if "live integration" in text:
        return ["action_provider_smoke", "pilot_env_handoff", "pilot_readiness"]
    if "unity catalog" in text:
        return ["unity_audit_smoke", "pilot_readiness"]
    return ["validation_suite"]


def _has_command(command_sets: dict[str, list[dict[str, str]]], name: str) -> bool:
    return any(command["name"] == name for commands in command_sets.values() for command in commands)


def _unique_command_names(gaps: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for gap in gaps:
        for name in gap["recommended_command_names"]:
            if name not in names:
                names.append(name)
    return names


def _commands_by_name(
    command_sets: dict[str, list[dict[str, str]]],
    names: list[str],
) -> list[dict[str, str]]:
    commands_by_name = {
        command["name"]: command
        for commands in command_sets.values()
        for command in commands
        if command["name"] in names
    }
    return [commands_by_name[name] for name in names if name in commands_by_name]
