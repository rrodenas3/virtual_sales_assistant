from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.governance.pilot_gaps import build_gap_report as build_gap_report_from_targets  # noqa: E402
from scripts.readiness_bundle import build_bundle  # noqa: E402

Target = Literal["local", "ai-demo", "pilot"]


def build_report(target: Target, *, bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    bundle = bundle or build_bundle(target)
    return build_report_from_bundle(target, bundle)


def build_report_from_bundle(target: Target, bundle: dict[str, Any]) -> dict[str, Any]:
    return build_gap_report_from_targets(target, bundle["pilot_readiness"]["activation_targets"])


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pilot_gap_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "pilot_gap_report.md").write_text(_markdown(report), encoding="utf-8")


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
