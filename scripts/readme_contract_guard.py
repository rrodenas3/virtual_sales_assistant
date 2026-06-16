from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

REQUIRED_SNIPPETS = [
    "PHANTOM VSA",
    "Port / Adapter / Factory",
    "Governance Before Integration",
    "Human-in-the-Loop",
    "GET  /api/v1/integrations/readiness",
    "GET  /api/v1/integrations/pilot-gap-report",
    "GET  /api/v1/integrations/activation-runbook",
    "GET  /api/v1/integrations/discovery-packet",
    "python scripts/pilot_readiness_report.py --target local",
    "python scripts/pilot_activation_runbook.py --target pilot",
    "docs/spec-compliance.md",
    "docs/implementation-continuation-plan.md",
    "docs/spec-corrections.md",
    "docs/architecture-ontology.md",
    "AGENTS.md",
]

REQUIRED_LINK_TARGETS = [
    "docs/phantom-vsa-architecture.png",
    "docs/spec-compliance.md",
    "docs/implementation-continuation-plan.md",
    "docs/spec-corrections.md",
    "docs/pilot-activation-runbook.md",
    "docs/architecture-ontology.md",
    "docs/infographic-5-unified-platform.md",
    "docs/pilot-metrics.md",
    "docs/client-discovery.md",
    "AGENTS.md",
]


def build_report() -> dict[str, Any]:
    readme_text = README.read_text(encoding="utf-8")
    missing_snippets = [snippet for snippet in REQUIRED_SNIPPETS if snippet not in readme_text]
    missing_targets = [target for target in REQUIRED_LINK_TARGETS if not (ROOT / target).exists()]
    stale_route_claims = _stale_route_claims(readme_text)
    checks = [
        {
            "name": "required_readme_snippets",
            "passed": not missing_snippets,
            "detail": missing_snippets,
        },
        {
            "name": "linked_targets_exist",
            "passed": not missing_targets,
            "detail": missing_targets,
        },
        {
            "name": "route_claims_not_stale",
            "passed": not stale_route_claims,
            "detail": stale_route_claims,
        },
    ]
    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "readme_contract_guard.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# README Contract Guard",
        "",
        f"- Passed: `{report['passed']}`",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for check in report["checks"]:
        detail = ", ".join(check["detail"]) if check["detail"] else "none"
        escaped_detail = detail.replace("|", "\\|")
        lines.append(f"| {check['name']} | {'pass' if check['passed'] else 'fail'} | {escaped_detail} |")
    (output_dir / "readme_contract_guard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _stale_route_claims(readme_text: str) -> list[str]:
    stale: list[str] = []
    api_contract = (ROOT / "backend" / "backend" / "api" / "contract.py").read_text(encoding="utf-8")
    current_required_routes = len(re.findall(r'"(?:GET|POST) /api/v1/', api_contract))
    match = re.search(r"\| API endpoints \| ([^|]+) \|", readme_text)
    if not match:
        stale.append("README missing Scale at a Glance API endpoints row")
        return stale
    claim = match.group(1).strip()
    if claim.endswith("+"):
        try:
            minimum = int(claim[:-1])
        except ValueError:
            stale.append(f"README API endpoint claim is not parseable: {claim}")
        else:
            if current_required_routes < minimum:
                stale.append(f"README claims {claim} endpoints but contract has {current_required_routes}")
    return stale


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate README architecture/API references against the implemented repo.")
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
