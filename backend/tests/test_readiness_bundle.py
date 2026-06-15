import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.readiness_bundle import build_bundle, write_artifacts  # noqa: E402


def test_readiness_bundle_combines_local_safe_artifacts() -> None:
    bundle = build_bundle("local")

    assert bundle["target"] == "local"
    assert bundle["passed"] is True
    assert bundle["pilot_readiness"]["passed"] is True
    assert bundle["mcp_smoke"]["server_count"] == 7
    assert "contracts" in bundle["live_data_contract_manifest"]
    assert bundle["required_manual_checks"]


def test_readiness_bundle_writes_handoff_artifacts(tmp_path) -> None:
    bundle = build_bundle("local")
    write_artifacts(bundle, tmp_path)

    assert json.loads((tmp_path / "readiness_bundle.json").read_text(encoding="utf-8"))["passed"] is True
    assert (tmp_path / "readiness_bundle.md").read_text(encoding="utf-8").startswith("# Readiness Bundle")
    assert (tmp_path / "readiness" / "pilot_readiness_report.json").exists()
    assert (tmp_path / "mcp" / "mcp_smoke_report.json").exists()
    assert (tmp_path / "contracts" / "live_data_contract_manifest.json").exists()
