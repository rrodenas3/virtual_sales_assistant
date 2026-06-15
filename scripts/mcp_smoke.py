from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

EXPECTED_TOOLS = {
    "crm": {"preview_visit_log_draft"},
    "manager": {"preview_manager_task_payload", "preview_manager_task_status_update"},
    "orders": {"preview_order_draft_payload"},
    "osa": {"get_oos_alerts", "get_phantom_inventory", "get_visit_priority"},
    "rgm": {"get_rgm_recommendations"},
    "shelf_image": {"analyze_shelf_image"},
    "store_master": {"get_store_health", "get_territory_stores"},
}


def collect_manifests() -> dict[str, dict[str, Any]]:
    manifests: dict[str, dict[str, Any]] = {}
    for server_name in sorted(EXPECTED_TOOLS):
        module = importlib.import_module(f"mcp.{server_name}.server")
        tools = getattr(module, "TOOLS")
        manifests[server_name] = {
            "server": server_name,
            "transport": "local-json",
            "tools": sorted(tools),
        }
    return manifests


def build_report() -> dict[str, Any]:
    manifests = collect_manifests()
    checks = []
    for server_name, expected_tools in sorted(EXPECTED_TOOLS.items()):
        manifest = manifests[server_name]
        actual_tools = set(manifest["tools"])
        checks.append(
            {
                "server": server_name,
                "passed": actual_tools == expected_tools and manifest["transport"] == "local-json",
                "expected_tools": sorted(expected_tools),
                "actual_tools": sorted(actual_tools),
                "transport": manifest["transport"],
            }
        )
    return {
        "passed": all(check["passed"] for check in checks),
        "server_count": len(checks),
        "checks": checks,
    }


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "mcp_smoke_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# MCP Smoke Report",
        "",
        f"- Passed: `{report['passed']}`",
        f"- Servers: `{report['server_count']}`",
        "",
        "| Server | Status | Transport | Tools |",
        "|---|---:|---|---|",
    ]
    for check in report["checks"]:
        status = "pass" if check["passed"] else "fail"
        lines.append(f"| {check['server']} | {status} | {check['transport']} | {', '.join(check['actual_tools'])} |")
    (output_dir / "mcp_smoke_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate local MCP server manifests.")
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
