from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.governance.activation import runtime_validation_commands  # noqa: E402
from backend.governance.live_contracts import contract_manifest  # noqa: E402
from scripts.mcp_smoke import build_report as build_mcp_smoke_report  # noqa: E402
from scripts.mcp_smoke import write_artifacts as write_mcp_smoke_artifacts  # noqa: E402
from scripts.pilot_readiness_report import build_report as build_pilot_readiness_report  # noqa: E402
from scripts.pilot_readiness_report import write_artifacts as write_pilot_readiness_artifacts  # noqa: E402
from scripts.validate_live_data_contracts import readiness_env_manifest  # noqa: E402


def build_bundle(target: str) -> dict[str, Any]:
    readiness = build_pilot_readiness_report(target)  # type: ignore[arg-type]
    mcp_smoke = build_mcp_smoke_report()
    manifest = {"contracts": contract_manifest()}
    return {
        "target": target,
        "passed": readiness["passed"] and mcp_smoke["passed"],
        "pilot_readiness": readiness,
        "mcp_smoke": mcp_smoke,
        "live_data_contract_manifest": manifest,
        "live_data_readiness_env_manifest": readiness_env_manifest(),
        "runtime_validation_commands": runtime_validation_commands(target),
        "required_manual_checks": [
            "Run public-safety scan before publishing or sharing artifacts.",
            "Run live data contract validation only in an approved credentialed environment.",
            "Run AI-demo readiness with the approved model provider before claiming AI assistant readiness.",
        ],
    }


def write_artifacts(bundle: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    readiness_dir = output_dir / "readiness"
    mcp_dir = output_dir / "mcp"
    contracts_dir = output_dir / "contracts"
    write_pilot_readiness_artifacts(bundle["pilot_readiness"], readiness_dir)
    write_mcp_smoke_artifacts(bundle["mcp_smoke"], mcp_dir)
    contracts_dir.mkdir(parents=True, exist_ok=True)
    (contracts_dir / "live_data_contract_manifest.json").write_text(
        json.dumps(bundle["live_data_contract_manifest"], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "readiness_bundle.json").write_text(
        json.dumps(bundle, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Readiness Bundle",
        "",
        f"- Target: `{bundle['target']}`",
        f"- Passed: `{bundle['passed']}`",
        "",
        "| Component | Status |",
        "|---|---:|",
        f"| Pilot readiness | {'pass' if bundle['pilot_readiness']['passed'] else 'fail'} |",
        f"| MCP smoke | {'pass' if bundle['mcp_smoke']['passed'] else 'fail'} |",
        f"| Contract manifest | {len(bundle['live_data_contract_manifest']['contracts'])} contracts |",
        "",
        "## Live Data Readiness Env",
        "",
        "| Env key | Meaning |",
        "|---|---|",
    ]
    for key, meaning in bundle["live_data_readiness_env_manifest"].items():
        escaped_meaning = str(meaning).replace("|", "\\|")
        lines.append(f"| `{key}` | {escaped_meaning} |")
    lines.extend(
        [
            "",
            "## Activation Targets",
            "",
            "| Target | Status | Blockers |",
            "|---|---:|---|",
        ]
    )
    for target in bundle["pilot_readiness"]["activation_targets"]:
        status = "ready" if target["ready"] else "blocked"
        blockers = ", ".join(target["blockers"]) or "none"
        escaped_blockers = blockers.replace("|", "\\|")
        lines.append(f"| {target['target']} | {status} | {escaped_blockers} |")
    lines.extend(
        [
            "",
            "## Runtime Validation Commands",
            "",
            "| Name | Command | Notes |",
            "|---|---|---|",
        ]
    )
    for command in bundle["runtime_validation_commands"]:
        escaped_command = str(command["command"]).replace("|", "\\|")
        escaped_notes = str(command["notes"]).replace("|", "\\|")
        lines.append(f"| {command['name']} | `{escaped_command}` | {escaped_notes} |")
    lines.extend(
        [
            "",
            "## Manual Checks",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in bundle["required_manual_checks"])
    (output_dir / "readiness_bundle.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a PHANTOM readiness handoff bundle.")
    parser.add_argument("--target", choices=["local", "ai-demo", "pilot"], default="local")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/readiness/bundle"))
    args = parser.parse_args()

    bundle = build_bundle(args.target)
    write_artifacts(bundle, args.output_dir)
    print(json.dumps(bundle, indent=2, sort_keys=True))
    if not bundle["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
