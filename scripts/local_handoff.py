from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from scripts.final_api_smoke import build_report as build_final_api_smoke_report  # noqa: E402
from scripts.final_api_smoke import write_artifacts as write_final_api_smoke_artifacts  # noqa: E402
from scripts.discovery_packet import build_report as build_discovery_packet  # noqa: E402
from scripts.discovery_packet import write_artifacts as write_discovery_packet_artifacts  # noqa: E402
from scripts.local_dev_smoke import build_report as build_local_dev_smoke_report  # noqa: E402
from scripts.local_dev_smoke import write_artifacts as write_local_dev_smoke_artifacts  # noqa: E402
from scripts.pilot_activation_runbook import build_report as build_pilot_activation_runbook  # noqa: E402
from scripts.pilot_activation_runbook import write_artifacts as write_pilot_activation_runbook_artifacts  # noqa: E402
from scripts.pilot_gap_report import build_report_from_bundle as build_pilot_gap_report  # noqa: E402
from scripts.pilot_gap_report import write_artifacts as write_pilot_gap_report_artifacts  # noqa: E402
from scripts.pilot_status_snapshot import build_snapshot as build_pilot_status_snapshot  # noqa: E402
from scripts.pilot_status_snapshot import write_artifacts as write_pilot_status_snapshot_artifacts  # noqa: E402
from scripts.readiness_bundle import build_bundle as build_readiness_bundle  # noqa: E402
from scripts.readiness_bundle import write_artifacts as write_readiness_bundle_artifacts  # noqa: E402
from scripts.seed_demo_data import build_demo_seed, validate_manifest as validate_demo_seed_manifest  # noqa: E402
from scripts.seed_demo_data import write_artifacts as write_demo_seed_artifacts  # noqa: E402
from scripts.spec_decision_guard import build_report as build_spec_decision_guard_report  # noqa: E402
from scripts.spec_decision_guard import write_artifacts as write_spec_decision_guard_artifacts  # noqa: E402
from scripts.validate_api_contract import build_local_contract  # noqa: E402
from scripts.validate_api_contract import write_artifacts as write_api_contract_artifacts  # noqa: E402


def build_handoff(
    target: str,
    *,
    run_public_safety: bool = True,
    run_local_dev_smoke: bool = False,
) -> dict[str, Any]:
    api_contract = build_local_contract()
    demo_seed = build_demo_seed()
    demo_seed_failures = validate_demo_seed_manifest(demo_seed["manifest"])
    final_api_smoke = build_final_api_smoke_report()
    discovery_packet = build_discovery_packet(target)  # type: ignore[arg-type]
    spec_decision_guard = build_spec_decision_guard_report()
    local_dev_smoke = (
        build_local_dev_smoke_report()
        if run_local_dev_smoke
        else {
            "passed": True,
            "skipped": True,
            "detail": "Skipped by operator flag; run scripts/local_dev_smoke.py after starting backend and frontend.",
        }
    )
    readiness_bundle = build_readiness_bundle(target)
    pilot_status_snapshot = build_pilot_status_snapshot(
        target,  # type: ignore[arg-type]
        bundle=readiness_bundle,
        api_contract=api_contract,
    )
    pilot_gap_report = build_pilot_gap_report(target, readiness_bundle)  # type: ignore[arg-type]
    pilot_activation_runbook = build_pilot_activation_runbook(target)  # type: ignore[arg-type]
    public_safety = (
        run_public_safety_scan()
        if run_public_safety
        else {
            "name": "public_safety_scan",
            "passed": True,
            "skipped": True,
            "detail": "Skipped by operator flag.",
        }
    )
    checks = [
        _check("api_contract", api_contract["valid"], _api_contract_detail(api_contract)),
        _check("demo_seed", not demo_seed_failures, _demo_seed_detail(demo_seed["manifest"], demo_seed_failures)),
        _check("discovery_packet", True, _discovery_packet_detail(discovery_packet)),
        _check("final_api_smoke", final_api_smoke["passed"], f"{len(final_api_smoke['checks'])} workflow checks"),
        _check("spec_decision_guard", spec_decision_guard["passed"], _spec_decision_guard_detail(spec_decision_guard)),
        _check("local_dev_smoke", local_dev_smoke["passed"], _local_dev_smoke_detail(local_dev_smoke)),
        _check("readiness_bundle", readiness_bundle["passed"], f"target={target}"),
        _check("pilot_status_snapshot", pilot_status_snapshot["passed"], _pilot_status_snapshot_detail(pilot_status_snapshot)),
        _check("pilot_gap_report", True, _pilot_gap_report_detail(pilot_gap_report)),
        _check("pilot_activation_runbook", True, _pilot_activation_runbook_detail(pilot_activation_runbook)),
        _check("public_safety_scan", public_safety["passed"], public_safety.get("detail", "")),
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "target": target,
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "artifacts": {
            "api_contract": "api-contract/api_contract_report.json",
            "demo_seed": "demo-data/demo_seed_manifest.json",
            "discovery_packet": "discovery-packet/discovery_packet.json",
            "final_api_smoke": "final-api-smoke/final_api_smoke.json",
            "spec_decision_guard": "spec-decision-guard/spec_decision_guard.json",
            "local_dev_smoke": "local-dev-smoke/local_dev_smoke.json",
            "readiness_bundle": "readiness-bundle/readiness_bundle.json",
            "pilot_status_snapshot": "pilot-status/pilot_status_snapshot.json",
            "pilot_gap_report": "pilot-gap-report/pilot_gap_report.json",
            "pilot_activation_runbook": "pilot-activation-runbook/pilot_activation_runbook.json",
            "local_handoff": "local_handoff.json",
        },
        "next_blocking_actions": readiness_bundle["handoff_summary"]["next_blocking_actions"],
        "api_contract": api_contract,
        "demo_seed": demo_seed,
        "discovery_packet": discovery_packet,
        "final_api_smoke": final_api_smoke,
        "spec_decision_guard": spec_decision_guard,
        "local_dev_smoke": local_dev_smoke,
        "readiness_bundle": readiness_bundle,
        "pilot_status_snapshot": pilot_status_snapshot,
        "pilot_gap_report": pilot_gap_report,
        "pilot_activation_runbook": pilot_activation_runbook,
        "public_safety_scan": public_safety,
    }


def write_artifacts(handoff: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_api_contract_artifacts(handoff["api_contract"], output_dir / "api-contract")
    write_demo_seed_artifacts(handoff["demo_seed"], output_dir / "demo-data")
    write_discovery_packet_artifacts(handoff["discovery_packet"], output_dir / "discovery-packet")
    write_final_api_smoke_artifacts(handoff["final_api_smoke"], output_dir / "final-api-smoke")
    write_spec_decision_guard_artifacts(handoff["spec_decision_guard"], output_dir / "spec-decision-guard")
    if handoff["local_dev_smoke"].get("skipped"):
        local_dev_dir = output_dir / "local-dev-smoke"
        local_dev_dir.mkdir(parents=True, exist_ok=True)
        (local_dev_dir / "local_dev_smoke.json").write_text(
            json.dumps(handoff["local_dev_smoke"], indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (local_dev_dir / "local_dev_smoke.md").write_text(
            "# Local Dev Smoke\n\n- Skipped: `true`\n",
            encoding="utf-8",
        )
    else:
        write_local_dev_smoke_artifacts(handoff["local_dev_smoke"], output_dir / "local-dev-smoke")
    write_readiness_bundle_artifacts(handoff["readiness_bundle"], output_dir / "readiness-bundle")
    write_pilot_status_snapshot_artifacts(handoff["pilot_status_snapshot"], output_dir / "pilot-status")
    write_pilot_gap_report_artifacts(handoff["pilot_gap_report"], output_dir / "pilot-gap-report")
    write_pilot_activation_runbook_artifacts(handoff["pilot_activation_runbook"], output_dir / "pilot-activation-runbook")
    (output_dir / "local_handoff.json").write_text(
        json.dumps(handoff, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "local_handoff.md").write_text(_handoff_markdown(handoff), encoding="utf-8")


def run_public_safety_scan() -> dict[str, Any]:
    result = subprocess.run(  # noqa: S603 - fixed local validation command, no shell interpolation.
        ["bash", "./scripts/public_safety_scan.sh"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return {
        "name": "public_safety_scan",
        "passed": result.returncode == 0,
        "returncode": result.returncode,
        "detail": f"exit={result.returncode}",
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }


def _handoff_markdown(handoff: dict[str, Any]) -> str:
    lines = [
        "# Local Handoff",
        "",
        f"- Generated at: `{handoff['generated_at']}`",
        f"- Target: `{handoff['target']}`",
        f"- Passed: `{handoff['passed']}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for check in handoff["checks"]:
        detail = str(check["detail"]).replace("|", "\\|")
        lines.append(f"| {check['name']} | {'pass' if check['passed'] else 'fail'} | {detail} |")
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
        ]
    )
    lines.extend(f"- `{path}`" for path in handoff["artifacts"].values())
    lines.extend(
        [
            "",
            "## Next Blocking Actions",
            "",
        ]
    )
    lines.extend(f"- {action}" for action in handoff["next_blocking_actions"])
    return "\n".join(lines) + "\n"


def _api_contract_detail(contract: dict[str, Any]) -> str:
    if contract["valid"]:
        return f"{contract['route_count']} routes"
    return (
        f"missing_routes={len(contract['missing_required_routes'])}; "
        f"missing_query_params={len(contract['missing_required_query_params'])}"
    )


def _demo_seed_detail(manifest: dict[str, Any], failures: list[str]) -> str:
    if failures:
        return "; ".join(failures)
    return f"{manifest['store_count']} stores; {manifest['alert_count']} alerts; reps={len(manifest['reps'])}"


def _discovery_packet_detail(report: dict[str, Any]) -> str:
    return (
        f"target={report['target']}; "
        f"missing={report['missing_count']}; "
        f"owners={len(report['owner_groups'])}"
    )


def _local_dev_smoke_detail(report: dict[str, Any]) -> str:
    if report.get("skipped"):
        return str(report["detail"])
    passed = sum(1 for check in report.get("checks", []) if check.get("passed"))
    total = len(report.get("checks", []))
    return f"{passed}/{total} live dev checks"


def _spec_decision_guard_detail(report: dict[str, Any]) -> str:
    failed = [check["name"] for check in report["checks"] if not check["passed"]]
    return "all locked decisions enforced" if not failed else f"failed={','.join(failed)}"


def _pilot_status_snapshot_detail(snapshot: dict[str, Any]) -> str:
    summary = snapshot["summary"]
    return (
        f"routes={summary['required_route_count']}; "
        f"commands={summary['runtime_command_count']}; "
        f"evidence_sections={summary['activation_evidence_sections']}"
    )


def _pilot_gap_report_detail(report: dict[str, Any]) -> str:
    return (
        f"ready_for_target={report['ready_for_requested_target']}; "
        f"gaps={report['gap_count']}; "
        f"commands={len(report['recommended_commands'])}"
    )


def _pilot_activation_runbook_detail(report: dict[str, Any]) -> str:
    return (
        f"phases={report['phase_count']}; "
        f"ready={report['ready_phase_count']}; "
        f"blocked={report['blocked_phase_count']}"
    )


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a public-safe PHANTOM local handoff artifact bundle.")
    parser.add_argument("--target", choices=["local", "ai-demo", "pilot"], default="local")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/local-handoff"))
    parser.add_argument("--skip-public-safety", action="store_true")
    parser.add_argument(
        "--include-local-dev-smoke",
        action="store_true",
        help="Also check the running Vite frontend and backend dev servers.",
    )
    args = parser.parse_args()

    handoff = build_handoff(
        args.target,
        run_public_safety=not args.skip_public_safety,
        run_local_dev_smoke=args.include_local_dev_smoke,
    )
    write_artifacts(handoff, args.output_dir)
    print(json.dumps(handoff, indent=2, sort_keys=True))
    if not handoff["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
