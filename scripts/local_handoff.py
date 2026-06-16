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
from scripts.readiness_bundle import build_bundle as build_readiness_bundle  # noqa: E402
from scripts.readiness_bundle import write_artifacts as write_readiness_bundle_artifacts  # noqa: E402
from scripts.seed_demo_data import build_demo_seed, validate_manifest as validate_demo_seed_manifest  # noqa: E402
from scripts.seed_demo_data import write_artifacts as write_demo_seed_artifacts  # noqa: E402
from scripts.validate_api_contract import build_local_contract  # noqa: E402
from scripts.validate_api_contract import write_artifacts as write_api_contract_artifacts  # noqa: E402


def build_handoff(target: str, *, run_public_safety: bool = True) -> dict[str, Any]:
    api_contract = build_local_contract()
    demo_seed = build_demo_seed()
    demo_seed_failures = validate_demo_seed_manifest(demo_seed["manifest"])
    final_api_smoke = build_final_api_smoke_report()
    readiness_bundle = build_readiness_bundle(target)
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
        _check("final_api_smoke", final_api_smoke["passed"], f"{len(final_api_smoke['checks'])} workflow checks"),
        _check("readiness_bundle", readiness_bundle["passed"], f"target={target}"),
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
            "final_api_smoke": "final-api-smoke/final_api_smoke.json",
            "readiness_bundle": "readiness-bundle/readiness_bundle.json",
            "local_handoff": "local_handoff.json",
        },
        "next_blocking_actions": readiness_bundle["handoff_summary"]["next_blocking_actions"],
        "api_contract": api_contract,
        "demo_seed": demo_seed,
        "final_api_smoke": final_api_smoke,
        "readiness_bundle": readiness_bundle,
        "public_safety_scan": public_safety,
    }


def write_artifacts(handoff: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_api_contract_artifacts(handoff["api_contract"], output_dir / "api-contract")
    write_demo_seed_artifacts(handoff["demo_seed"], output_dir / "demo-data")
    write_final_api_smoke_artifacts(handoff["final_api_smoke"], output_dir / "final-api-smoke")
    write_readiness_bundle_artifacts(handoff["readiness_bundle"], output_dir / "readiness-bundle")
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


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a public-safe PHANTOM local handoff artifact bundle.")
    parser.add_argument("--target", choices=["local", "ai-demo", "pilot"], default="local")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/local-handoff"))
    parser.add_argument("--skip-public-safety", action="store_true")
    args = parser.parse_args()

    handoff = build_handoff(args.target, run_public_safety=not args.skip_public_safety)
    write_artifacts(handoff, args.output_dir)
    print(json.dumps(handoff, indent=2, sort_keys=True))
    if not handoff["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
