import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.mcp_smoke import build_report, write_artifacts  # noqa: E402


def test_mcp_smoke_report_covers_all_local_servers() -> None:
    report = build_report()

    assert report["passed"] is True
    assert report["server_count"] == 7
    servers = {check["server"] for check in report["checks"]}
    assert servers == {"crm", "manager", "orders", "osa", "rgm", "shelf_image", "store_master"}
    osa = next(check for check in report["checks"] if check["server"] == "osa")
    assert osa["actual_tools"] == ["get_oos_alerts", "get_phantom_inventory", "get_visit_priority"]


def test_mcp_smoke_writes_artifacts(tmp_path) -> None:
    report = build_report()

    write_artifacts(report, tmp_path)

    assert json.loads((tmp_path / "mcp_smoke_report.json").read_text(encoding="utf-8"))["passed"] is True
    assert "store_master" in (tmp_path / "mcp_smoke_report.md").read_text(encoding="utf-8")
