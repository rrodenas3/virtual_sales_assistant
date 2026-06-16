import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.local_handoff import build_handoff, write_artifacts  # noqa: E402


def test_local_handoff_combines_operator_proof_bundle() -> None:
    handoff = build_handoff("local", run_public_safety=False)

    assert handoff["target"] == "local"
    assert handoff["passed"] is True
    assert handoff["public_safety_scan"]["skipped"] is True
    assert handoff["api_contract"]["valid"] is True
    assert handoff["demo_seed"]["manifest"]["alert_count"] == 125
    assert handoff["final_api_smoke"]["passed"] is True
    assert handoff["local_dev_smoke"]["skipped"] is True
    assert handoff["readiness_bundle"]["passed"] is True
    assert handoff["next_blocking_actions"]
    check_names = {check["name"] for check in handoff["checks"]}
    assert check_names == {
        "api_contract",
        "demo_seed",
        "final_api_smoke",
        "local_dev_smoke",
        "readiness_bundle",
        "public_safety_scan",
    }


def test_local_handoff_can_include_running_dev_smoke(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.local_handoff.build_local_dev_smoke_report",
        lambda: {"passed": True, "checks": [{"passed": True}, {"passed": True}]},
    )

    handoff = build_handoff("local", run_public_safety=False, run_local_dev_smoke=True)

    assert handoff["passed"] is True
    assert handoff["local_dev_smoke"]["passed"] is True
    assert next(check for check in handoff["checks"] if check["name"] == "local_dev_smoke")["detail"] == (
        "2/2 live dev checks"
    )


def test_local_handoff_writes_nested_artifacts(tmp_path: Path) -> None:
    handoff = build_handoff("local", run_public_safety=False)

    write_artifacts(handoff, tmp_path)

    assert json.loads((tmp_path / "local_handoff.json").read_text(encoding="utf-8"))["passed"] is True
    handoff_md = (tmp_path / "local_handoff.md").read_text(encoding="utf-8")
    assert handoff_md.startswith("# Local Handoff")
    assert "## Checks" in handoff_md
    assert "## Next Blocking Actions" in handoff_md
    assert (tmp_path / "api-contract" / "api_contract_report.json").exists()
    assert (tmp_path / "api-contract" / "api_contract_report.md").exists()
    assert (tmp_path / "demo-data" / "demo_seed_manifest.json").exists()
    assert (tmp_path / "demo-data" / "store_master_seed.json").exists()
    assert (tmp_path / "demo-data" / "oos_alert_seed.json").exists()
    assert (tmp_path / "final-api-smoke" / "final_api_smoke.json").exists()
    assert (tmp_path / "final-api-smoke" / "final_api_smoke.md").exists()
    assert (tmp_path / "local-dev-smoke" / "local_dev_smoke.json").exists()
    assert (tmp_path / "local-dev-smoke" / "local_dev_smoke.md").exists()
    assert (tmp_path / "readiness-bundle" / "readiness_bundle.json").exists()
    assert (tmp_path / "readiness-bundle" / "readiness_bundle.md").exists()
