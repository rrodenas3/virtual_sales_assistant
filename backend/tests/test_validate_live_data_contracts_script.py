import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.validate_live_data_contracts import (  # noqa: E402
    build_manifest_payload,
    readiness_env_manifest,
    write_artifacts,
    write_manifest_artifacts,
)


def test_live_contract_script_writes_readiness_artifacts(tmp_path) -> None:
    report = {
        "valid": True,
        "generated_at": "2026-06-15T08:00:00+00:00",
        "territory_code": "WEST-01",
        "rep_id": "REP-001",
        "store_id": "ST-001",
        "results": [
            {
                "name": "databricks_osa_alerts",
                "valid": True,
                "row_count": 50,
                "missing_columns": [],
                "violations": [],
            },
            {
                "name": "snowflake_store_master",
                "valid": True,
                "row_count": 1,
                "missing_columns": [],
                "violations": [],
            },
        ],
    }

    write_artifacts(report, tmp_path)

    readiness = json.loads((tmp_path / "readiness_env.json").read_text(encoding="utf-8"))
    assert readiness == {
        "LIVE_DATA_CONTRACT_VALIDATED": True,
        "LIVE_DATA_CONTRACT_LAST_VALIDATION_AT": "2026-06-15T08:00:00+00:00",
        "LIVE_DATA_CONTRACT_VALIDATION_SUMMARY": "2/2 contracts valid; rows=51",
    }
    assert "databricks_osa_alerts" in (tmp_path / "live_data_contract_report.md").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "live_data_contract_report.json").read_text(encoding="utf-8"))["valid"] is True


def test_readiness_env_manifest_declares_operator_keys() -> None:
    manifest = readiness_env_manifest()

    assert set(manifest) == {
        "LIVE_DATA_CONTRACT_VALIDATED",
        "LIVE_DATA_CONTRACT_LAST_VALIDATION_AT",
        "LIVE_DATA_CONTRACT_VALIDATION_SUMMARY",
    }


def test_manifest_payload_documents_columns_and_failure_examples(tmp_path: Path) -> None:
    manifest = build_manifest_payload()

    assert "databricks_osa_alerts" in manifest["contracts"]
    assert "risk_score" in manifest["contracts"]["databricks_osa_alerts"]["required_columns"]
    assert "LIVE_DATA_CONTRACT_VALIDATED" in manifest["readiness_env_manifest"]
    assert "filter_leakage" in manifest["failure_examples"]

    write_manifest_artifacts(manifest, tmp_path)

    manifest_json = json.loads((tmp_path / "live_data_contract_manifest.json").read_text(encoding="utf-8"))
    manifest_md = (tmp_path / "live_data_contract_manifest.md").read_text(encoding="utf-8")
    assert manifest_json["failure_examples"]["score_range"]
    assert "## Common Failure Examples" in manifest_md
    assert "databricks_osa_alerts" in manifest_md
