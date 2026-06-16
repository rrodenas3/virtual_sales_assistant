import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pilot_readiness_report import _discovery_owner_blockers, build_report, write_artifacts  # noqa: E402


def test_local_readiness_report_includes_scaffold_smoke() -> None:
    report = build_report("local")

    assert report["passed"], report
    smoke = report["scaffold_smoke"]
    assert smoke["passed"] is True
    assert {check["name"] for check in smoke["checks"]} == {
        "hitl_order_smoke",
        "manager_task_smoke",
        "shelf_image_smoke",
    }
    assert report["mcp_smoke"]["passed"] is True
    assert report["mcp_smoke"]["server_count"] == 7
    assert report["memory"]["ready"] is True
    assert report["action_providers"]["ready"] is True
    assert report["data_platform"]["ready"] is True
    assert report["auth"]["ready"] is True
    assert report["shelf_image"]["ready"] is True
    assert report["audit"]["ready"] is True
    assert report["observability"]["ready"] is True
    assert report["discovery_owner_blockers"] == {}
    assert {command["name"] for command in report["runtime_validation_commands"]} == {
        "public_safety_scan",
        "local_readiness",
        "api_contract",
        "demo_seed",
        "final_api_smoke",
        "local_dev_smoke",
    }
    assert report["ai_demo_eval_validated"] is False
    targets = {target["target"]: target for target in report["activation_targets"]}
    assert targets["local"]["ready"] is True
    assert targets["ai-demo"]["ready"] is False
    assert targets["pilot"]["ready"] is False
    assert any(gate["name"] == "scaffold_smoke" and gate["passed"] for gate in report["gates"])
    assert any(gate["name"] == "mcp_smoke" and gate["passed"] for gate in report["gates"])
    assert any(gate["name"] == "memory_provider" and gate["passed"] for gate in report["gates"])
    assert any(gate["name"] == "action_providers" and gate["passed"] for gate in report["gates"])
    assert any(gate["name"] == "data_platform" and gate["passed"] for gate in report["gates"])
    assert any(gate["name"] == "auth_provider" and gate["passed"] for gate in report["gates"])
    assert any(gate["name"] == "shelf_image_provider" and gate["passed"] for gate in report["gates"])
    assert any(gate["name"] == "audit_sink" and gate["passed"] for gate in report["gates"])
    assert any(gate["name"] == "observability" and gate["passed"] for gate in report["gates"])
    assert any(gate["name"] == "ai_demo_eval_evidence" and gate["passed"] for gate in report["gates"])


def test_discovery_owner_blockers_group_by_owner() -> None:
    owners = _discovery_owner_blockers(["discovery_data_sharing_model", "guardrail_classifier_endpoint"])

    assert owners["delivery"] == ["discovery_data_sharing_model"]
    assert owners["shared"] == ["guardrail_classifier_endpoint"]


def test_readiness_report_writes_runtime_commands(tmp_path) -> None:
    report = build_report("local")

    write_artifacts(report, tmp_path)

    report_md = (tmp_path / "pilot_readiness_report.md").read_text(encoding="utf-8")
    assert "## Runtime Validation Commands" in report_md
    assert "public_safety_scan" in report_md
