from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable or "python"


@dataclass(frozen=True)
class VerificationCommand:
    name: str
    cwd: Path
    args: list[str]
    display_args: list[str] | None = None
    timeout_seconds: int = 300

    @property
    def display(self) -> str:
        return " ".join(self.display_args or self.args)


def build_command_plan(
    *,
    include_frontend_e2e: bool = False,
    include_alembic: bool = False,
    run_public_safety: bool = True,
) -> list[VerificationCommand]:
    commands = [
        VerificationCommand(
            "backend_ruff",
            ROOT / "backend",
            [PYTHON, "-m", "ruff", "check", "backend", "tests", "alembic", "../mcp", "../scripts"],
            ["python", "-m", "ruff", "check", "backend", "tests", "alembic", "../mcp", "../scripts"],
        ),
        VerificationCommand(
            "backend_pytest",
            ROOT / "backend",
            [PYTHON, "-m", "pytest", "tests", "-q"],
            ["python", "-m", "pytest", "tests", "-q"],
        ),
        VerificationCommand("local_eval", ROOT / "backend", [PYTHON, "../scripts/run_eval.py"], ["python", "../scripts/run_eval.py"]),
        VerificationCommand(
            "local_readiness_report",
            ROOT / "backend",
            [PYTHON, "../scripts/pilot_readiness_report.py", "--target", "local"],
            ["python", "../scripts/pilot_readiness_report.py", "--target", "local"],
        ),
        VerificationCommand(
            "live_contract_manifest",
            ROOT / "backend",
            [PYTHON, "../scripts/validate_live_data_contracts.py", "--manifest-only"],
            ["python", "../scripts/validate_live_data_contracts.py", "--manifest-only"],
        ),
        VerificationCommand("mcp_smoke", ROOT / "backend", [PYTHON, "../scripts/mcp_smoke.py"], ["python", "../scripts/mcp_smoke.py"]),
        VerificationCommand(
            "spec_decision_guard",
            ROOT / "backend",
            [PYTHON, "../scripts/spec_decision_guard.py", "--output-dir", "../artifacts/spec-decision-guard/local"],
            ["python", "../scripts/spec_decision_guard.py", "--output-dir", "../artifacts/spec-decision-guard/local"],
        ),
        VerificationCommand(
            "validation_suite",
            ROOT / "backend",
            [
                PYTHON,
                "../scripts/validation_suite.py",
                "--target",
                "local",
                "--skip-public-safety",
                "--output-dir",
                "../artifacts/validation-suite/local",
            ],
            [
                "python",
                "../scripts/validation_suite.py",
                "--target",
                "local",
                "--skip-public-safety",
                "--output-dir",
                "../artifacts/validation-suite/local",
            ],
        ),
        VerificationCommand(
            "frontend_build",
            ROOT / "frontend",
            [_executable("npm"), "run", "build"],
            ["npm", "run", "build"],
            timeout_seconds=420,
        ),
    ]
    if include_frontend_e2e:
        commands.append(
            VerificationCommand(
                "frontend_e2e",
                ROOT / "frontend",
                [_executable("npm"), "run", "test:e2e"],
                ["npm", "run", "test:e2e"],
                timeout_seconds=600,
            )
        )
    if include_alembic:
        commands.append(
            VerificationCommand(
                "alembic_upgrade",
                ROOT / "backend",
                [_executable("alembic"), "upgrade", "head"],
                ["alembic", "upgrade", "head"],
            )
        )
    if run_public_safety:
        commands.append(
            VerificationCommand(
                "public_safety_scan",
                ROOT,
                [_executable("bash"), "./scripts/public_safety_scan.sh"],
                ["bash", "./scripts/public_safety_scan.sh"],
                timeout_seconds=120,
            )
        )
    return commands


def run_plan(commands: list[VerificationCommand]) -> dict[str, Any]:
    results = [_run_command(command) for command in commands]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "passed": all(result["passed"] for result in results),
        "root": "<repo-root>",
        "commands": results,
    }


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "local_verification.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "local_verification.md").write_text(_markdown(report), encoding="utf-8")


def _run_command(command: VerificationCommand) -> dict[str, Any]:
    started_at = datetime.now(UTC)
    try:
        result = subprocess.run(  # noqa: S603 - arguments are fixed by this script, not user-supplied shell text.
            command.args,
            cwd=command.cwd,
            capture_output=True,
            text=True,
            timeout=command.timeout_seconds,
            check=False,
        )
        return {
            "name": command.name,
            "command": _sanitize_text(command.display),
            "cwd": _relative_cwd(command.cwd),
            "passed": result.returncode == 0,
            "returncode": result.returncode,
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
            "stdout_tail": _sanitize_text(result.stdout[-4000:]),
            "stderr_tail": _sanitize_text(result.stderr[-4000:]),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "name": command.name,
            "command": _sanitize_text(command.display),
            "cwd": _relative_cwd(command.cwd),
            "passed": False,
            "returncode": None,
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
            "stdout_tail": _sanitize_text((exc.stdout or "")[-4000:]) if isinstance(exc.stdout, str) else "",
            "stderr_tail": _sanitize_text((exc.stderr or "")[-4000:]) if isinstance(exc.stderr, str) else "",
            "error": f"Timed out after {command.timeout_seconds}s",
        }
    except OSError as exc:
        return {
            "name": command.name,
            "command": _sanitize_text(command.display),
            "cwd": _relative_cwd(command.cwd),
            "passed": False,
            "returncode": None,
            "started_at": started_at.isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
            "stdout_tail": "",
            "stderr_tail": _sanitize_text(str(exc)),
            "error": type(exc).__name__,
        }


def _executable(name: str) -> str:
    return shutil.which(name) or name


def _sanitize_text(value: str) -> str:
    home = str(Path.home())
    root = str(ROOT)
    sanitized = value.replace(root, "<repo-root>")
    sanitized = sanitized.replace(home, "<user-home>")
    sanitized = re.sub(r"[A-Za-z]:[/\\]Users[/\\][^/\\\s]+", "<user-home>", sanitized)
    sanitized = sanitized.replace("\\", "/")
    return sanitized


def _relative_cwd(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Local Verification",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Passed: `{report['passed']}`",
        "",
        "| Check | Status | CWD | Command |",
        "|---|---:|---|---|",
    ]
    for command in report["commands"]:
        status = "pass" if command["passed"] else "fail"
        escaped_command = str(command["command"]).replace("|", "\\|")
        lines.append(f"| {command['name']} | {status} | `{command['cwd']}` | `{escaped_command}` |")
    failed = [command for command in report["commands"] if not command["passed"]]
    if failed:
        lines.extend(["", "## Failed Command Output", ""])
        for command in failed:
            lines.extend(
                [
                    f"### {command['name']}",
                    "",
                    "```text",
                    command.get("stderr_tail") or command.get("stdout_tail") or command.get("error", ""),
                    "```",
                    "",
                ]
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local public-safe verification checks from the repo root.")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/local-verification"))
    parser.add_argument("--include-frontend-e2e", action="store_true")
    parser.add_argument("--include-alembic", action="store_true")
    parser.add_argument("--skip-public-safety", action="store_true")
    args = parser.parse_args()

    report = run_plan(
        build_command_plan(
            include_frontend_e2e=args.include_frontend_e2e,
            include_alembic=args.include_alembic,
            run_public_safety=not args.skip_public_safety,
        )
    )
    write_artifacts(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
