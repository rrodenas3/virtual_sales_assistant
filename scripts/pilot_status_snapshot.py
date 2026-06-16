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

from scripts.readiness_bundle import build_bundle  # noqa: E402
from scripts.validate_api_contract import build_local_contract  # noqa: E402

Target = Literal["local", "ai-demo", "pilot"]


def build_snapshot(
    target: Target,
    *,
    bundle: dict[str, Any] | None = None,
    api_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundle = bundle or build_bundle(target)
    api_contract = api_contract or build_local_contract()
    readiness = bundle["pilot_readiness"]
    evidence = bundle["activation_evidence_manifest"]
    runtime_commands = bundle["runtime_validation_commands"]
    activation_targets = readiness["activation_targets"]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "target": target,
        "passed": bundle["passed"] and api_contract["valid"],
        "summary": {
            "readiness_passed": bundle["passed"],
            "api_contract_valid": api_contract["valid"],
            "api_route_count": api_contract["route_count"],
            "required_route_count": len(api_contract["required_routes"]),
            "mcp_server_count": bundle["mcp_smoke"]["server_count"],
            "runtime_command_count": len(runtime_commands),
            "activation_evidence_sections": len(evidence["sections"]),
        },
        "activation_targets": [
            {
                "target": item["target"],
                "ready": item["ready"],
                "blocker_count": len(item["blockers"]),
                "blockers": item["blockers"],
            }
            for item in activation_targets
        ],
        "runtime_commands": [
            {"name": command["name"], "command": command["command"]}
            for command in runtime_commands
        ],
        "evidence": {
            "target": evidence["target"],
            "required_artifacts": evidence["required_artifacts"],
            "required_env_keys": evidence["required_env_keys"],
            "sections": [
                {
                    "name": section["name"],
                    "artifact_count": len(section["artifacts"]),
                    "env_key_count": len(section["env_keys"]),
                }
                for section in evidence["sections"]
            ],
        },
        "next_blocking_actions": bundle["handoff_summary"]["next_blocking_actions"],
        "manual_checks": bundle["required_manual_checks"],
    }


def write_artifacts(snapshot: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pilot_status_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "pilot_status_snapshot.md").write_text(_markdown(snapshot), encoding="utf-8")


def _markdown(snapshot: dict[str, Any]) -> str:
    summary = snapshot["summary"]
    lines = [
        "# Pilot Status Snapshot",
        "",
        f"- Generated at: `{snapshot['generated_at']}`",
        f"- Target: `{snapshot['target']}`",
        f"- Passed: `{snapshot['passed']}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Readiness passed | {summary['readiness_passed']} |",
        f"| API contract valid | {summary['api_contract_valid']} |",
        f"| API routes | {summary['api_route_count']} |",
        f"| Required routes | {summary['required_route_count']} |",
        f"| MCP servers | {summary['mcp_server_count']} |",
        f"| Runtime commands | {summary['runtime_command_count']} |",
        f"| Evidence sections | {summary['activation_evidence_sections']} |",
        "",
        "## Activation Targets",
        "",
        "| Target | Status | Blockers |",
        "|---|---:|---|",
    ]
    for target in snapshot["activation_targets"]:
        status = "ready" if target["ready"] else "blocked"
        blockers = ", ".join(target["blockers"]) or "none"
        escaped_blockers = blockers.replace("|", "\\|")
        lines.append(f"| {target['target']} | {status} | {escaped_blockers} |")
    lines.extend(
        [
            "",
            "## Runtime Commands",
            "",
            "| Name | Command |",
            "|---|---|",
        ]
    )
    for command in snapshot["runtime_commands"]:
        escaped_command = str(command["command"]).replace("|", "\\|")
        lines.append(f"| {command['name']} | `{escaped_command}` |")
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            f"- Required artifacts: `{len(snapshot['evidence']['required_artifacts'])}`",
            f"- Required env keys: `{len(snapshot['evidence']['required_env_keys'])}`",
            "",
            "| Section | Artifacts | Env keys |",
            "|---|---:|---:|",
        ]
    )
    for section in snapshot["evidence"]["sections"]:
        lines.append(f"| {section['name']} | {section['artifact_count']} | {section['env_key_count']} |")
    lines.extend(["", "## Next Blocking Actions", ""])
    lines.extend(f"- {action}" for action in snapshot["next_blocking_actions"])
    lines.extend(["", "## Manual Checks", ""])
    lines.extend(f"- {check}" for check in snapshot["manual_checks"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a public-safe pilot status snapshot.")
    parser.add_argument("--target", choices=["local", "ai-demo", "pilot"], default="local")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/pilot-status"))
    args = parser.parse_args()

    snapshot = build_snapshot(args.target)  # type: ignore[arg-type]
    write_artifacts(snapshot, args.output_dir)
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    if not snapshot["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
