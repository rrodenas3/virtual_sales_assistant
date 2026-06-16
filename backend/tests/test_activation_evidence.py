import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.governance.activation_evidence import build_evidence_manifest  # noqa: E402


def test_local_evidence_manifest_is_scaffold_only() -> None:
    manifest = build_evidence_manifest("local")

    assert manifest["target"] == "local"
    assert [section["name"] for section in manifest["sections"]] == ["local_scaffold"]
    assert manifest["required_env_keys"] == []
    assert "local-handoff/spec-decision-guard/spec_decision_guard.json" in manifest["required_artifacts"]


def test_ai_demo_evidence_manifest_requires_provider_eval_env() -> None:
    manifest = build_evidence_manifest("ai-demo")

    section_names = {section["name"] for section in manifest["sections"]}
    assert section_names == {"local_scaffold", "ai_demo_eval"}
    assert "AI_DEMO_EVAL_VALIDATED" in manifest["required_env_keys"]
    assert "eval-ai/ai_demo_eval_env.json" in manifest["required_artifacts"]
    assert "load/summary/load_test_report.json" in manifest["required_artifacts"]


def test_pilot_evidence_manifest_requires_live_contract_and_handoff_env() -> None:
    manifest = build_evidence_manifest("pilot")

    section_names = {section["name"] for section in manifest["sections"]}
    assert {
        "local_scaffold",
        "ai_demo_eval",
        "live_data_contracts",
        "provider_dry_runs",
        "pilot_env_handoff",
    } == section_names
    assert "LIVE_DATA_CONTRACT_VALIDATED" in manifest["required_env_keys"]
    assert "pilot-env/pilot_validation.env.snippet" in manifest["required_artifacts"]
    assert "unity-audit-smoke/unity_audit_smoke.json" in manifest["required_artifacts"]
