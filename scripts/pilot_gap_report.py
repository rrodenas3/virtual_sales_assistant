from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.governance.activation import runtime_validation_command_sets  # noqa: E402
from scripts.readiness_bundle import build_bundle  # noqa: E402

Target = Literal["local", "ai-demo", "pilot"]

ROADMAP_ITEMS = [
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


def build_report(target: Target, *, bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    bundle = bundle or build_bundle(target)
    return build_report_from_bundle(target, bundle)


def build_report_from_bundle(target: Target, bundle: dict[str, Any]) -> dict[str, Any]:
    activation_targets = bundle["pilot_readiness"]["activation_targets"]
    command_sets = runtime_validation_command_sets()
    requested_target = next(item for item in activation_targets if item["target"] == target)
    gaps = [
        _gap_for_blocker(target_body["target"], blocker, command_sets)
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


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pilot_gap_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "pilot_gap_report.md").write_text(_markdown(report), encoding="utf-8")


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


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Pilot Gap Report",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Target: `{report['target']}`",
        f"- Ready for requested target: `{report['ready_for_requested_target']}`",
        f"- Blocking gaps: `{report['gap_count']}`",
        "",
        "## Activation Targets",
        "",
        "| Target | Status | Blockers |",
        "|---|---:|---:|",
    ]
    for target in report["activation_targets"]:
        status = "ready" if target["ready"] else "blocked"
        lines.append(f"| {target['target']} | {status} | {target['blocker_count']} |")
    lines.extend(["", "## Blocking Gaps", "", "| Target | Owner | Blocker | Commands |", "|---|---|---|---|"])
    for gap in report["blocking_gaps"]:
        blocker = str(gap["blocker"]).replace("|", "\\|")
        commands = ", ".join(gap["recommended_command_names"]) or "validation_suite"
        lines.append(f"| {gap['target']} | {gap['owner']} | {blocker} | {commands} |")
    lines.extend(["", "## Recommended Commands", "", "| Name | Command |", "|---|---|"])
    for command in report["recommended_commands"]:
        command_text = str(command["command"]).replace("|", "\\|")
        lines.append(f"| {command['name']} | `{command_text}` |")
    lines.extend(["", "## Roadmap Items", "", "| Area | Owner | Status | Next gate |", "|---|---|---|---|"])
    for item in report["roadmap_items"]:
        lines.append(f"| {item['area']} | {item['owner']} | {item['status']} | {item['next_gate']} |")
    lines.extend(["", "## Public Safety", ""])
    lines.extend(f"- {note}" for note in report["public_safety_notes"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a public-safe pilot gap report.")
    parser.add_argument("--target", choices=["local", "ai-demo", "pilot"], default="local")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/pilot-gap-report"))
    args = parser.parse_args()

    report = build_report(args.target)  # type: ignore[arg-type]
    write_artifacts(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
