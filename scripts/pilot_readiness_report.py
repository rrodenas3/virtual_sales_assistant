from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from backend.config import settings  # noqa: E402
from backend.governance.discovery import readiness_blockers, selected_live_modes  # noqa: E402
from tests.eval.run_eval import run_eval  # noqa: E402

Target = Literal["local", "ai-demo", "pilot"]


def _gate(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail}


def build_report(target: Target) -> dict[str, Any]:
    required_provider = "anthropic" if target in {"ai-demo", "pilot"} else None
    eval_result = run_eval(require_provider=required_provider)
    modes = selected_live_modes()
    blockers = readiness_blockers()
    providers = eval_result["summary"]["providers"]

    gates = [
        _gate("eval", eval_result["passed"], f"providers={providers}; failures={eval_result['failures']}"),
        _gate(
            "real_ai",
            required_provider is None or required_provider in providers,
            "not required for local scaffold" if required_provider is None else f"requires provider={required_provider}",
        ),
        _gate(
            "discovery",
            not blockers,
            "no selected live modes" if not modes else f"blockers={blockers}",
        ),
        _gate(
            "live_data_contract",
            target != "pilot" or settings.live_data_contract_validated,
            "required for pilot target" if target == "pilot" else "not required for local or AI demo target",
        ),
        _gate(
            "summary_provider_config",
            target == "local" or settings.summary_provider == "anthropic",
            f"SUMMARY_PROVIDER={settings.summary_provider}",
        ),
        _gate(
            "agent_stream",
            target == "local" or settings.agent_run_enabled,
            f"AGENT_RUN_ENABLED={settings.agent_run_enabled}",
        ),
        _gate(
            "audit_sink",
            target != "pilot" or settings.audit_sink == "unity_catalog" or settings.audit_dual_write_enabled,
            f"AUDIT_SINK={settings.audit_sink}; AUDIT_DUAL_WRITE_ENABLED={settings.audit_dual_write_enabled}",
        ),
    ]
    return {
        "target": target,
        "passed": all(gate["passed"] for gate in gates),
        "selected_live_modes": sorted(modes),
        "discovery_blockers": blockers,
        "eval_summary": eval_result["summary"],
        "gates": gates,
    }


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pilot_readiness_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Pilot Readiness Report",
        "",
        f"- Target: `{report['target']}`",
        f"- Passed: `{report['passed']}`",
        f"- Selected live modes: `{', '.join(report['selected_live_modes']) or 'none'}`",
        "",
        "| Gate | Status | Detail |",
        "|---|---:|---|",
    ]
    for gate in report["gates"]:
        status = "pass" if gate["passed"] else "fail"
        detail = str(gate["detail"]).replace("|", "\\|")
        lines.append(f"| {gate['name']} | {status} | {detail} |")
    (output_dir / "pilot_readiness_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PHANTOM VSA readiness gates for local, AI demo, or pilot.")
    parser.add_argument("--target", choices=["local", "ai-demo", "pilot"], default="local")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    report = build_report(args.target)
    if args.output_dir:
        write_artifacts(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
