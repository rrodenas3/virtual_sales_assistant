import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate_api_contract import REQUIRED_ROUTES, build_local_contract, write_artifacts  # noqa: E402


def test_local_api_contract_contains_pilot_routes() -> None:
    contract = build_local_contract()

    assert contract["valid"] is True
    assert contract["missing_required_routes"] == []
    assert contract["missing_required_query_params"] == []
    assert "GET /api/v1/integrations/readiness" in contract["available_routes"]
    assert "GET /api/v1/integrations/readiness" in contract["required_routes"]
    assert "GET /api/v1/manager/approval-queue?territory_code=WEST-01" in REQUIRED_ROUTES
    assert "GET /api/v1/manager/my-tasks?status=OPEN" in REQUIRED_ROUTES


def test_api_contract_writes_handoff_artifacts(tmp_path: Path) -> None:
    contract = build_local_contract()

    write_artifacts(contract, tmp_path)

    assert json.loads((tmp_path / "api_contract_report.json").read_text(encoding="utf-8"))["valid"] is True
    markdown = (tmp_path / "api_contract_report.md").read_text(encoding="utf-8")
    assert markdown.startswith("# API Contract Report")
    assert "GET /api/v1/integrations/readiness" in markdown
    assert "Missing required query params: `none`" in markdown
    assert "## Available Routes" in markdown
    assert "GET /api/v1/manager/tasks?status&territory_code" in markdown
