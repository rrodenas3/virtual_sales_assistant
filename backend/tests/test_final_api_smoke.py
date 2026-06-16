import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.final_api_smoke import build_report, write_artifacts  # noqa: E402


def test_final_api_smoke_exercises_core_workflow() -> None:
    report = build_report()

    assert report["passed"], report
    check_names = {check["name"] for check in report["checks"]}
    assert {
        "rep_priority_route",
        "rep_store_detail",
        "rep_oos_alerts",
        "rep_grounded_summary",
        "rep_alert_feedback",
        "rep_order_draft",
        "manager_approval_queue",
        "manager_approval",
        "rep_order_submit_sandbox",
        "manager_task_create",
        "manager_readiness_payload_contract",
        "rep_task_complete",
        "admin_audit_feed",
    } <= check_names
    assert report["context"]["summary_audit_event_id"]
    assert report["context"]["submit_audit_event_id"]
    assert report["context"]["metric_feedback_count"] >= 1
    assert report["context"]["readiness_targets"] == ["local", "ai-demo", "pilot"]
    assert report["context"]["readiness_evidence_targets"] == ["ai-demo", "local", "pilot"]


def test_final_api_smoke_writes_handoff_artifacts(tmp_path: Path) -> None:
    report = build_report()

    write_artifacts(report, tmp_path)

    assert json.loads((tmp_path / "final_api_smoke.json").read_text(encoding="utf-8"))["passed"] is True
    markdown = (tmp_path / "final_api_smoke.md").read_text(encoding="utf-8")
    assert markdown.startswith("# Final API Smoke")
    assert "rep_grounded_summary" in markdown
    assert "manager_readiness_payload_contract" in markdown
