from __future__ import annotations

import argparse
import base64
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def token(claims: dict[str, Any]) -> str:
    def enc(data: dict[str, Any]) -> str:
        raw = json.dumps(data, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{enc({'alg': 'none', 'typ': 'JWT'})}.{enc(claims)}."


REP_TOKEN = token({"sub": "REP-001", "territory_code": "WEST-01", "role": "rep"})
MANAGER_TOKEN = token({"sub": "MGR-001", "territory_code": "WEST-01", "role": "manager"})
ADMIN_TOKEN = token({"sub": "ADMIN-001", "role": "admin"})


def build_report() -> dict[str, Any]:
    session_id = f"final-smoke-{uuid4()}"
    checks: list[dict[str, Any]] = []
    context: dict[str, Any] = {"session_id": session_id}

    with _client(REP_TOKEN) as rep:
        visits = _request(checks, "rep_priority_route", rep.get, "/api/v1/visits/today?territory_code=WEST-01")
        top_store = visits.json()[0]
        store_id = top_store["store_id"]
        context["store_id"] = store_id

        store = _request(checks, "rep_store_detail", rep.get, f"/api/v1/stores/{store_id}")
        alerts = _request(checks, "rep_oos_alerts", rep.get, f"/api/v1/stores/{store_id}/alerts?limit=2")
        rgm = _request(checks, "rep_rgm_recommendations", rep.get, f"/api/v1/stores/{store_id}/rgm-recommendations")
        alert = alerts.json()["alerts"][0]
        context["alert_id"] = alert["alert_id"]
        context["sku_id"] = alert["sku_id"]

        summary = _request(
            checks,
            "rep_grounded_summary",
            rep.post,
            "/api/v1/agent/osa-summary",
            json={
                "territory_code": "WEST-01",
                "store_id": store_id,
                "session_id": session_id,
                "alert_ids": [alert["alert_id"]],
            },
        )
        feedback = _request(
            checks,
            "rep_alert_feedback",
            rep.post,
            f"/api/v1/alerts/{alert['alert_id']}/feedback",
            json={"feedback": "confirmed", "session_id": session_id, "notes": "final api smoke"},
        )
        audit = _request(checks, "rep_session_audit", rep.get, f"/api/v1/audit/session/{session_id}")

        draft = _request(
            checks,
            "rep_order_draft",
            rep.post,
            "/api/v1/orders/drafts",
            json={
                "store_id": store_id,
                "session_id": session_id,
                "items": [
                    {
                        "sku_id": alert["sku_id"],
                        "sku_name": alert["sku_name"],
                        "quantity": 12,
                        "reason": alert["recommended_action"],
                    }
                ],
                "notes": "final api smoke",
            },
        )
        draft_id = draft.json()["draft_id"]
        context["draft_id"] = draft_id

        crm = _request(
            checks,
            "rep_crm_visit_draft",
            rep.post,
            "/api/v1/crm/visit-log-drafts",
            json={
                "store_id": store_id,
                "session_id": session_id,
                "notes": "Final API smoke visit log",
                "outcome": "completed",
            },
        )

    with _client(MANAGER_TOKEN) as manager:
        _request(checks, "manager_territory_summary", manager.get, "/api/v1/manager/territory-summary?territory_code=WEST-01")
        queue = _request(checks, "manager_approval_queue", manager.get, "/api/v1/manager/approval-queue?territory_code=WEST-01")
        approval = _request(
            checks,
            "manager_approval",
            manager.post,
            f"/api/v1/approvals/{draft_id}/approve",
            json={"notes": "final api smoke"},
        )
        task = _request(
            checks,
            "manager_task_create",
            manager.post,
            "/api/v1/manager/tasks",
            json={
                "territory_code": "WEST-01",
                "store_id": store_id,
                "assigned_rep_id": "REP-001",
                "session_id": session_id,
                "title": "Final smoke shelf check",
                "task_type": "shelf_check",
                "priority": "medium",
                "linked_alert_ids": [alert["alert_id"]],
            },
        )
        context["task_id"] = task.json()["task_id"]
        readiness = _request(checks, "manager_readiness", manager.get, "/api/v1/integrations/readiness")
        _check_readiness_payload(checks, readiness.json())

    with _client(REP_TOKEN) as rep:
        submit = _request(checks, "rep_order_submit_sandbox", rep.post, f"/api/v1/orders/drafts/{draft_id}/submit-sandbox")
        _request(
            checks,
            "rep_task_complete",
            rep.post,
            f"/api/v1/manager/tasks/{context['task_id']}/status",
            json={"status": "COMPLETED", "session_id": session_id},
        )
        metrics = _request(checks, "rep_pilot_metrics", rep.get, "/api/v1/metrics/pilot")

    with _client(ADMIN_TOKEN) as admin:
        admin_events = _request(checks, "admin_audit_feed", admin.get, "/api/v1/admin/audit-events?limit=5")
        event_id = admin_events.json()["events"][0]["event_id"]
        _request(checks, "admin_audit_detail", admin.get, f"/api/v1/admin/audit-events/{event_id}")

    return {
        "passed": all(check["passed"] for check in checks),
        "generated_at": datetime.now(UTC).isoformat(),
        "context": {
            **context,
            "summary_audit_event_id": summary.json().get("audit_event_id"),
            "feedback_audit_event_id": feedback.json().get("audit_event_id"),
            "crm_audit_event_id": crm.json().get("audit_event_id"),
            "approval_audit_event_id": approval.json().get("audit_event_id"),
            "submit_audit_event_id": submit.json().get("audit_event_id"),
            "metric_feedback_count": metrics.json().get("feedback_count"),
            "approval_queue_count": queue.json().get("pending_count"),
            "readiness_targets": [target.get("target") for target in readiness.json().get("activation_targets", [])],
            "readiness_evidence_targets": sorted(readiness.json().get("activation_evidence_manifests", {})),
            "store_name": store.json().get("store_name"),
            "rgm_audit_event_id": rgm.json().get("audit_event_id"),
            "audit_event_count": len(audit.json().get("events", [])),
        },
        "checks": checks,
    }


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "final_api_smoke.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Final API Smoke",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Passed: `{report['passed']}`",
        f"- Session: `{report['context']['session_id']}`",
        f"- Store: `{report['context']['store_id']}`",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for check in report["checks"]:
        detail = str(check["detail"]).replace("|", "\\|")
        lines.append(f"| {check['name']} | {'pass' if check['passed'] else 'fail'} | {detail} |")
    (output_dir / "final_api_smoke.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _client(jwt: str) -> TestClient:
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {jwt}"})
    return client


def _request(checks: list[dict[str, Any]], name: str, method: Any, path: str, **kwargs: Any) -> Any:
    response = method(path, **kwargs)
    passed = 200 <= response.status_code < 300
    checks.append(
        {
            "name": name,
            "passed": passed,
            "status_code": response.status_code,
            "detail": _detail(response),
        }
    )
    if not passed:
        raise RuntimeError(f"{name} failed: {response.status_code} {response.text}")
    return response


def _detail(response: Any) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:120]
    if isinstance(body, list):
        return f"items={len(body)}"
    if isinstance(body, dict):
        keys = ["store_id", "alert_id", "draft_id", "audit_event_id", "task_id", "pending_count", "feedback_count"]
        parts = [f"{key}={body[key]}" for key in keys if key in body]
        return "; ".join(parts) or f"keys={','.join(sorted(body)[:5])}"
    return str(body)


def _check_readiness_payload(checks: list[dict[str, Any]], body: dict[str, Any]) -> None:
    targets = {target.get("target") for target in body.get("activation_targets", []) if isinstance(target, dict)}
    command_sets = body.get("runtime_validation_commands", {})
    evidence_sets = body.get("activation_evidence_manifests", {})
    required_targets = {"local", "ai-demo", "pilot"}
    missing_targets = sorted(required_targets - targets)
    missing_commands = sorted(target for target in required_targets if target not in command_sets)
    missing_evidence = sorted(target for target in required_targets if target not in evidence_sets)
    missing_pilot_env = "pilot-env/pilot_validation.env.snippet" not in evidence_sets.get("pilot", {}).get(
        "required_artifacts",
        [],
    )
    passed = not missing_targets and not missing_commands and not missing_evidence and not missing_pilot_env
    detail_parts = [
        f"targets={','.join(sorted(targets)) or 'none'}",
        f"commands={','.join(sorted(command_sets)) or 'none'}",
        f"evidence={','.join(sorted(evidence_sets)) or 'none'}",
    ]
    if missing_targets:
        detail_parts.append(f"missing_targets={','.join(missing_targets)}")
    if missing_commands:
        detail_parts.append(f"missing_commands={','.join(missing_commands)}")
    if missing_evidence:
        detail_parts.append(f"missing_evidence={','.join(missing_evidence)}")
    if missing_pilot_env:
        detail_parts.append("missing_pilot_env_handoff=true")
    checks.append(
        {
            "name": "manager_readiness_payload_contract",
            "passed": passed,
            "status_code": 200 if passed else 500,
            "detail": "; ".join(detail_parts),
        }
    )
    if not passed:
        raise RuntimeError(f"manager_readiness_payload_contract failed: {'; '.join(detail_parts)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PHANTOM final local API smoke workflow.")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/final-api-smoke"))
    args = parser.parse_args()

    report = build_report()
    write_artifacts(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
