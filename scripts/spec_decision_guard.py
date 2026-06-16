from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_DEPENDENCIES = {
    "backend/pyproject.toml": ["langgraph", "langchain", "langchain-anthropic"],
    "frontend/package.json": ["@copilotkit/react-core", "@copilotkit/react-ui", "@copilotkit/runtime"],
}

REQUIRED_TEXT = {
    "docs/spec-corrections.md": [
        "LangGraph is not a required dependency for Phase 1",
        "Do not install the `langgraph` package",
        "CopilotKit is permanently replaced by the custom `/agent/run` SSE bridge for Phase 1",
        "Do not install the `@copilotkit/*` packages",
    ],
    "docs/spec-compliance.md": [
        "LangGraph is not required for pilot readiness per correction #9",
        "custom `/agent/run` SSE bridge formally replaces CopilotKit for Phase 1 per correction #10",
        "Correction #9 makes plain async node functions the pilot orchestration layer",
        "Correction #10 formally replaces CopilotKit/AG-UI with the custom `/agent/run` SSE assistant panel",
    ],
    "docs/implementation-continuation-plan.md": [
        "LangGraph: not a required dependency for Phase 1 (spec correction #9)",
        "CopilotKit: permanently replaced by the custom `/agent/run` SSE bridge for Phase 1 (spec correction #10)",
        "Multi-agent mesh (Supervisor + Action Agent): Phase 2 scope",
    ],
    "AGENTS.md": [
        "LangGraph not required for Phase 1 (spec correction #9)",
        "CopilotKit formally replaced, not just deferred (spec correction #10)",
        "Plain async functions are the Phase 1 architecture (spec correction #9)",
        "permanently replaced by the custom SSE bridge for Phase 1 (spec correction #10)",
    ],
}


def build_report() -> dict[str, Any]:
    checks = [_check_forbidden_dependencies(), _check_required_text()]
    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "spec_decision_guard.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Spec Decision Guard",
        "",
        f"- Passed: `{report['passed']}`",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for check in report["checks"]:
        detail = str(check["detail"]).replace("|", "\\|")
        lines.append(f"| {check['name']} | {'pass' if check['passed'] else 'fail'} | {detail} |")
    (output_dir / "spec_decision_guard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _check_forbidden_dependencies() -> dict[str, Any]:
    failures: list[str] = []
    for relative_path, forbidden in FORBIDDEN_DEPENDENCIES.items():
        text = _read(relative_path)
        lowered = text.lower()
        for dependency in forbidden:
            if re.search(rf'["\']{re.escape(dependency.lower())}(?:["\']|[<>=~!])', lowered):
                failures.append(f"{relative_path}:{dependency}")
    return {
        "name": "forbidden_dependencies",
        "passed": not failures,
        "detail": ", ".join(failures) or "none",
    }


def _check_required_text() -> dict[str, Any]:
    missing: list[str] = []
    for relative_path, snippets in REQUIRED_TEXT.items():
        text = _read(relative_path)
        for snippet in snippets:
            if snippet not in text:
                missing.append(f"{relative_path}:{snippet}")
    return {
        "name": "locked_decision_text",
        "passed": not missing,
        "detail": "; ".join(missing) or "all locked decision text present",
    }


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate PHANTOM locked spec decisions.")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    report = build_report()
    if args.output_dir:
        write_artifacts(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
