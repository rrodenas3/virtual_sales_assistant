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

from backend.governance.activation import runtime_validation_commands  # noqa: E402
from scripts.local_handoff import build_handoff, write_artifacts as write_handoff_artifacts  # noqa: E402

Target = Literal["local", "ai-demo", "pilot"]


def build_suite(
    target: Target,
    *,
    include_local_dev_smoke: bool = False,
    run_public_safety: bool = True,
) -> dict[str, Any]:
    handoff = build_handoff(
        target,
        run_public_safety=run_public_safety,
        run_local_dev_smoke=include_local_dev_smoke,
    )
    readiness = handoff["readiness_bundle"]["pilot_readiness"]
    commands = runtime_validation_commands(target)
    suite_command = next(command for command in commands if command["name"] == "validation_suite")
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "target": target,
        "passed": handoff["passed"],
        "suite_command": suite_command["command"],
        "include_local_dev_smoke": include_local_dev_smoke,
        "public_safety_ran": not handoff["public_safety_scan"].get("skipped", False),
        "checks": handoff["checks"],
        "activation_targets": readiness["activation_targets"],
        "runtime_validation_commands": commands,
        "next_blocking_actions": handoff["next_blocking_actions"],
        "artifacts": {
            "validation_suite": "validation_suite.json",
            "local_handoff": "local-handoff/local_handoff.json",
            **{f"local_handoff_{name}": f"local-handoff/{path}" for name, path in handoff["artifacts"].items()},
        },
        "local_handoff": handoff,
    }


def write_artifacts(suite: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_handoff_artifacts(suite["local_handoff"], output_dir / "local-handoff")
    (output_dir / "validation_suite.json").write_text(
        json.dumps(suite, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "validation_suite.md").write_text(_markdown(suite), encoding="utf-8")


def _markdown(suite: dict[str, Any]) -> str:
    lines = [
        "# Validation Suite",
        "",
        f"- Generated at: `{suite['generated_at']}`",
        f"- Target: `{suite['target']}`",
        f"- Passed: `{suite['passed']}`",
        f"- Suite command: `{suite['suite_command']}`",
        f"- Public safety ran: `{suite['public_safety_ran']}`",
        f"- Local dev smoke included: `{suite['include_local_dev_smoke']}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for check in suite["checks"]:
        detail = str(check["detail"]).replace("|", "\\|")
        lines.append(f"| {check['name']} | {'pass' if check['passed'] else 'fail'} | {detail} |")
    lines.extend(
        [
            "",
            "## Activation Targets",
            "",
            "| Target | Status | Blockers |",
            "|---|---:|---|",
        ]
    )
    for target in suite["activation_targets"]:
        blockers = ", ".join(target["blockers"]) or "none"
        escaped_blockers = blockers.replace("|", "\\|")
        status = "ready" if target["ready"] else "blocked"
        lines.append(f"| {target['target']} | {status} | {escaped_blockers} |")
    lines.extend(
        [
            "",
            "## Runtime Validation Commands",
            "",
            "| Name | Command |",
            "|---|---|",
        ]
    )
    for command in suite["runtime_validation_commands"]:
        escaped = str(command["command"]).replace("|", "\\|")
        lines.append(f"| {command['name']} | `{escaped}` |")
    lines.extend(["", "## Next Blocking Actions", ""])
    lines.extend(f"- {action}" for action in suite["next_blocking_actions"])
    lines.extend(["", "## Artifacts", ""])
    lines.extend(f"- `{path}`" for path in suite["artifacts"].values())
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PHANTOM validation suite for a target handoff.")
    parser.add_argument("--target", choices=["local", "ai-demo", "pilot"], default="local")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/validation-suite"))
    parser.add_argument("--skip-public-safety", action="store_true")
    parser.add_argument(
        "--include-local-dev-smoke",
        action="store_true",
        help="Also check the running Vite frontend and backend dev servers.",
    )
    args = parser.parse_args()

    suite = build_suite(
        args.target,
        include_local_dev_smoke=args.include_local_dev_smoke,
        run_public_safety=not args.skip_public_safety,
    )
    write_artifacts(suite, args.output_dir)
    print(json.dumps(suite, indent=2, sort_keys=True))
    if not suite["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
