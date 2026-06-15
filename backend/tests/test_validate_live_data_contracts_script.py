import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.validate_live_data_contracts import write_artifacts  # noqa: E402


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
