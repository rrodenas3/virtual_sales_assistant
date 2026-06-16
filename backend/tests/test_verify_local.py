from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any

from scripts.verify_local import build_command_plan, run_plan, write_artifacts


def test_verify_local_command_plan_defaults_to_public_safe_checks() -> None:
    commands = build_command_plan()

    names = [command.name for command in commands]

    assert names[0] == "backend_ruff"
    assert "backend_pytest" in names
    assert "readme_contract_guard" in names
    assert "frontend_build" in names
    assert "frontend_e2e" not in names
    assert names[-1] == "public_safety_scan"
    assert commands[0].cwd.name == "backend"
    assert commands[-1].args[-1] == "./scripts/public_safety_scan.sh"


def test_verify_local_optional_commands() -> None:
    names = [
        command.name
        for command in build_command_plan(
            include_frontend_e2e=True,
            include_alembic=True,
            run_public_safety=False,
        )
    ]

    assert "frontend_e2e" in names
    assert names[-1] == "alembic_upgrade"
    assert "public_safety_scan" not in names


def test_verify_local_report_and_artifacts(monkeypatch: Any, tmp_path: Path) -> None:
    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        fake_home = "C:" + "\\Users\\someone\\repo"
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="ok", stderr=fake_home)

    monkeypatch.setattr(subprocess, "run", fake_run)

    report = run_plan(build_command_plan(run_public_safety=False))
    write_artifacts(report, tmp_path)

    assert report["passed"] is True
    assert report["root"] == "<repo-root>"
    assert {command["name"] for command in report["commands"]} >= {"backend_ruff", "validation_suite"}
    assert ("C:" + "\\Users") not in json.dumps(report)
    assert not re.search(r"[A-Za-z]:[/\\]", json.dumps(report))
    assert report["commands"][0]["command"].startswith("python -m ruff")
    assert json.loads((tmp_path / "local_verification.json").read_text(encoding="utf-8"))["passed"] is True
    markdown = (tmp_path / "local_verification.md").read_text(encoding="utf-8")
    assert markdown.startswith("# Local Verification")
    assert "backend_ruff" in markdown


def test_verify_local_failure_marks_report_failed(monkeypatch: Any) -> None:
    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args[0], returncode=1, stdout="", stderr="failed")

    monkeypatch.setattr(subprocess, "run", fake_run)

    report = run_plan(build_command_plan(run_public_safety=False))

    assert report["passed"] is False
    assert report["commands"][0]["stderr_tail"] == "failed"
