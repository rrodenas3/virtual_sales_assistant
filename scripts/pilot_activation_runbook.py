from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.governance.activation import runtime_validation_command_sets  # noqa: E402
from backend.governance.activation_runbook import build_activation_runbook  # noqa: E402
from backend.governance.guardrails import guardrail_status  # noqa: E402
from backend.governance.offline_agent import offline_agent_status  # noqa: E402
from backend.services.telemetry import observability_status  # noqa: E402
from scripts.pilot_readiness_report import build_report as build_pilot_readiness_report  # noqa: E402

Target = Literal["local", "ai-demo", "pilot"]


def build_report(target: Target) -> dict[str, Any]:
    readiness = build_pilot_readiness_report(target)
    provider_readiness = {
        "auth": readiness["auth"],
        "data_platform": readiness["data_platform"],
        "action_providers": readiness["action_providers"],
        "shelf_image": readiness["shelf_image"],
        "memory": readiness["memory"],
        "audit": readiness["audit"],
        "guardrails": readiness.get("guardrails", guardrail_status()),
        "offline_agent": readiness.get("offline_agent", offline_agent_status()),
        "observability": readiness.get("observability", observability_status()),
    }
    return build_activation_runbook(
        current_target=target,
        activation_targets=readiness["activation_targets"],
        provider_readiness=provider_readiness,
        runtime_validation_commands=runtime_validation_command_sets(),
    )


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pilot_activation_runbook.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "pilot_activation_runbook.md").write_text(_markdown(report), encoding="utf-8")


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Pilot Activation Runbook",
        "",
        f"- Current target: `{report['current_target']}`",
        f"- Phase count: `{report['phase_count']}`",
        f"- Ready phases: `{report['ready_phase_count']}`",
        f"- Blocked phases: `{report['blocked_phase_count']}`",
        "",
        "## Final Outcome",
        "",
        report["final_outcome"],
        "",
        "## Phase Plan",
        "",
        "| Phase | Status | Owner | Effort | Commands | Blockers |",
        "|---|---:|---|---|---|---|",
    ]
    for phase in report["phases"]:
        commands = ", ".join(phase["required_command_names"]) or "none"
        blockers = ", ".join(phase["blockers"][:3]) or "none"
        lines.append(
            "| "
            + " | ".join(
                [
                    phase["title"].replace("|", "\\|"),
                    phase["status"],
                    phase["owner"],
                    phase["estimated_effort"].replace("|", "\\|"),
                    commands.replace("|", "\\|"),
                    blockers.replace("|", "\\|"),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Public Safety", ""])
    lines.extend(f"- {note}" for note in report["public_safety_notes"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the public-safe final VSA activation phase plan.")
    parser.add_argument("--target", choices=["local", "ai-demo", "pilot"], default="pilot")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/pilot-activation-runbook"))
    args = parser.parse_args()

    report = build_report(args.target)  # type: ignore[arg-type]
    write_artifacts(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
