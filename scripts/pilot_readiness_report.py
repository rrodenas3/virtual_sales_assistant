from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.config import settings  # noqa: E402
from backend.governance.action_providers import action_provider_status  # noqa: E402
from backend.governance.data_platform import data_platform_status  # noqa: E402
from backend.governance.discovery import readiness_blockers, selected_live_modes  # noqa: E402
from backend.main import app  # noqa: E402
from backend.memory.adapters import memory_status  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from scripts.mcp_smoke import build_report as build_mcp_smoke_report  # noqa: E402
from tests.eval.run_eval import run_eval  # noqa: E402

Target = Literal["local", "ai-demo", "pilot"]

REP_TOKEN = (
    "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0."
    "eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."
)
MANAGER_TOKEN = (
    "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0."
    "eyJzdWIiOiJNR1ItMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6Im1hbmFnZXIifQ."
)


def _gate(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail}


def _client(token: str) -> TestClient:
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def run_scaffold_smoke() -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    with _client(REP_TOKEN) as rep:
        alerts_response = rep.get("/api/v1/stores/ST-001/alerts?limit=2")
        alerts = alerts_response.json()["alerts"] if alerts_response.status_code == 200 else []
        alert = alerts[0] if alerts else {}
        draft_response = rep.post(
            "/api/v1/orders/drafts",
            json={
                "store_id": "ST-001",
                "session_id": "readiness_order",
                "items": [
                    {
                        "sku_id": alert.get("sku_id", "SKU-4001"),
                        "sku_name": alert.get("sku_name", "Core SKU 4001"),
                        "quantity": 12,
                        "reason": alert.get("recommended_action", "Readiness smoke"),
                    }
                ],
            },
        )
        draft = draft_response.json() if draft_response.status_code == 200 else {}
        approval_response = rep.post(f"/api/v1/approvals/{draft.get('draft_id', 'missing')}/approve", json={"notes": "ok"})
        submit_response = rep.post(f"/api/v1/orders/drafts/{draft.get('draft_id', 'missing')}/submit-sandbox")
        results.append(
            _gate(
                "hitl_order_smoke",
                draft_response.status_code == 200
                and approval_response.status_code == 200
                and submit_response.status_code == 200,
                f"draft={draft_response.status_code}; approval={approval_response.status_code}; submit={submit_response.status_code}",
            )
        )

        shelf_response = rep.post(
            "/api/v1/stores/ST-001/shelf-image-analysis",
            json={
                "store_id": "ST-001",
                "session_id": "readiness_shelf",
                "image_ref": "upload://readiness/image_1",
                "alert_ids": [alert["alert_id"]] if alert else [],
            },
        )
        shelf_body = shelf_response.json() if shelf_response.status_code == 200 else {}
        results.append(
            _gate(
                "shelf_image_smoke",
                shelf_response.status_code == 200 and bool(shelf_body.get("audit_event_id")),
                f"status={shelf_response.status_code}; findings={len(shelf_body.get('findings', []))}",
            )
        )

    with _client(MANAGER_TOKEN) as manager:
        task_response = manager.post(
            "/api/v1/manager/tasks",
            json={
                "territory_code": "WEST-01",
                "store_id": "ST-001",
                "assigned_rep_id": "REP-001",
                "session_id": "readiness_manager_task",
                "title": "Readiness shelf check",
                "task_type": "shelf_check",
                "priority": "medium",
            },
        )
        task = task_response.json() if task_response.status_code == 200 else {}

    with _client(REP_TOKEN) as rep:
        task_status_response = rep.post(
            f"/api/v1/manager/tasks/{task.get('task_id', 'missing')}/status",
            json={"status": "COMPLETED", "session_id": "readiness_manager_task_done"},
        )
        results.append(
            _gate(
                "manager_task_smoke",
                task_response.status_code == 200 and task_status_response.status_code == 200,
                f"create={task_response.status_code}; status={task_status_response.status_code}",
            )
        )

    return {
        "passed": all(result["passed"] for result in results),
        "checks": results,
    }


def build_report(target: Target) -> dict[str, Any]:
    required_provider = "anthropic" if target in {"ai-demo", "pilot"} else None
    eval_result = run_eval(require_provider=required_provider)
    smoke_result = run_scaffold_smoke()
    mcp_smoke = build_mcp_smoke_report()
    memory = memory_status()
    action_providers = action_provider_status()
    data_platform = data_platform_status()
    modes = selected_live_modes()
    blockers = readiness_blockers()
    providers = eval_result["summary"]["providers"]
    action_provider_detail = (
        f"crm={action_providers['crm']['provider']}; "
        f"erp={action_providers['erp']['provider']}; "
        f"blockers={action_providers['blockers']}"
    )
    data_platform_detail = (
        f"databricks_selected={data_platform['databricks']['selected']}; "
        f"snowflake_selected={data_platform['snowflake']['selected']}; "
        f"blockers={data_platform['blockers']}"
    )

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
        _gate(
            "scaffold_smoke",
            smoke_result["passed"],
            "; ".join(f"{check['name']}={check['passed']}" for check in smoke_result["checks"]),
        ),
        _gate(
            "mcp_smoke",
            mcp_smoke["passed"],
            f"servers={mcp_smoke['server_count']}",
        ),
        _gate(
            "memory_provider",
            memory["ready"],
            f"provider={memory['provider']}; blockers={memory['blockers']}",
        ),
        _gate(
            "action_providers",
            action_providers["ready"],
            action_provider_detail,
        ),
        _gate(
            "data_platform",
            data_platform["ready"],
            data_platform_detail,
        ),
    ]
    return {
        "target": target,
        "passed": all(gate["passed"] for gate in gates),
        "selected_live_modes": sorted(modes),
        "discovery_blockers": blockers,
        "eval_summary": eval_result["summary"],
        "scaffold_smoke": smoke_result,
        "mcp_smoke": mcp_smoke,
        "memory": memory,
        "action_providers": action_providers,
        "data_platform": data_platform,
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
