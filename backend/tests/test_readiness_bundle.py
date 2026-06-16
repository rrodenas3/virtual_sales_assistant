import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.governance.activation import runtime_validation_command_sets  # noqa: E402
from scripts.readiness_bundle import build_bundle, write_artifacts  # noqa: E402


def test_readiness_bundle_combines_local_safe_artifacts() -> None:
    bundle = build_bundle("local")

    assert bundle["target"] == "local"
    assert bundle["passed"] is True
    assert bundle["handoff_summary"]["target"] == "local"
    assert bundle["handoff_summary"]["next_blocking_actions"]
    assert bundle["pilot_readiness"]["passed"] is True
    assert bundle["mcp_smoke"]["server_count"] == 7
    assert "contracts" in bundle["live_data_contract_manifest"]
    assert "failure_examples" in bundle["live_data_contract_manifest"]
    assert "LIVE_DATA_CONTRACT_VALIDATED" in bundle["live_data_readiness_env_manifest"]
    assert bundle["activation_evidence_manifest"]["target"] == "local"
    assert bundle["activation_evidence_manifest"]["sections"][0]["name"] == "local_scaffold"
    command_names = {command["name"] for command in bundle["runtime_validation_commands"]}
    assert command_names == {
        "public_safety_scan",
        "spec_decision_guard",
        "local_readiness",
        "api_contract",
        "demo_seed",
        "final_api_smoke",
        "local_dev_smoke",
        "local_verification",
        "pilot_status_snapshot",
        "pilot_gap_report",
        "pilot_activation_runbook",
        "validation_suite",
    }
    assert bundle["required_manual_checks"]


def test_readiness_bundle_includes_pilot_runtime_commands() -> None:
    bundle = build_bundle("pilot")
    command_names = {command["name"] for command in bundle["runtime_validation_commands"]}

    assert {
        "public_safety_scan",
        "local_readiness",
        "api_contract",
        "final_api_smoke",
        "local_verification",
        "pilot_status_snapshot",
        "pilot_gap_report",
        "pilot_activation_runbook",
        "ai_demo_readiness",
        "summary_load_test",
        "live_data_contracts",
        "pilot_readiness",
        "validation_suite",
    } <= command_names


def test_runtime_validation_command_sets_cover_all_targets() -> None:
    command_sets = runtime_validation_command_sets()

    assert set(command_sets) == {"local", "ai-demo", "pilot"}
    assert command_sets["local"][0]["name"] == "public_safety_scan"
    assert command_sets["local"][1]["name"] == "spec_decision_guard"
    assert any(command["name"] == "api_contract" for command in command_sets["local"])
    assert any(command["name"] == "demo_seed" for command in command_sets["local"])
    assert any(command["name"] == "final_api_smoke" for command in command_sets["local"])
    assert any(command["name"] == "local_dev_smoke" for command in command_sets["local"])
    assert any(command["name"] == "local_verification" for command in command_sets["local"])
    assert any(command["name"] == "pilot_status_snapshot" for command in command_sets["local"])
    assert any(command["name"] == "pilot_gap_report" for command in command_sets["local"])
    assert any(command["name"] == "pilot_activation_runbook" for command in command_sets["local"])
    assert command_sets["local"][-1]["name"] == "validation_suite"
    assert "--include-local-dev-smoke" in command_sets["local"][-1]["command"]
    assert any(command["name"] == "summary_load_test" for command in command_sets["ai-demo"])
    assert any(command["name"] == "ai_summary_eval" for command in command_sets["ai-demo"])
    assert any(command["name"] == "mlflow_handoff_dry_run" for command in command_sets["ai-demo"])
    assert any(command["name"] == "ai_demo_eval_evidence" for command in command_sets["ai-demo"])
    assert any(command["name"] == "live_data_contracts" for command in command_sets["pilot"])
    assert any(command["name"] == "unity_audit_smoke" for command in command_sets["pilot"])
    assert any(command["name"] == "action_provider_smoke" for command in command_sets["pilot"])
    assert any(command["name"] == "guardrail_classifier_smoke" for command in command_sets["pilot"])
    assert any(command["name"] == "memory_provider_smoke" for command in command_sets["pilot"])
    assert any(command["name"] == "pilot_env_handoff" for command in command_sets["pilot"])
    assert any(command["name"] == "pilot_status_snapshot" for command in command_sets["pilot"])
    assert any(command["name"] == "pilot_gap_report" for command in command_sets["pilot"])
    assert any(command["name"] == "pilot_activation_runbook" for command in command_sets["pilot"])
    assert command_sets["pilot"][-1]["name"] == "validation_suite"


def test_readiness_bundle_writes_handoff_artifacts(tmp_path) -> None:
    bundle = build_bundle("local")
    write_artifacts(bundle, tmp_path)

    assert json.loads((tmp_path / "readiness_bundle.json").read_text(encoding="utf-8"))["passed"] is True
    bundle_md = (tmp_path / "readiness_bundle.md").read_text(encoding="utf-8")
    assert bundle_md.startswith("# Readiness Bundle")
    assert "## Handoff Summary" in bundle_md
    assert "## Activation Targets" in bundle_md
    assert "## Runtime Validation Commands" in bundle_md
    assert "## Activation Evidence" in bundle_md
    assert "public_safety_scan" in bundle_md
    assert "## Live Data Readiness Env" in bundle_md
    assert "`LIVE_DATA_CONTRACT_VALIDATED`" in bundle_md
    assert "| ai-demo | blocked |" in bundle_md
    assert "## AI Demo Readiness Env" in bundle_md
    assert "## Discovery Blocker Owners" in (tmp_path / "readiness" / "pilot_readiness_report.md").read_text(encoding="utf-8")
    assert (tmp_path / "readiness" / "pilot_readiness_report.json").exists()
    assert (tmp_path / "mcp" / "mcp_smoke_report.json").exists()
    assert (tmp_path / "contracts" / "live_data_contract_manifest.json").exists()
    assert (tmp_path / "contracts" / "live_data_contract_manifest.md").exists()
