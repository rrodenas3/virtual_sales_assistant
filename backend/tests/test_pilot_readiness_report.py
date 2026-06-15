import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pilot_readiness_report import build_report  # noqa: E402


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
    assert any(gate["name"] == "scaffold_smoke" and gate["passed"] for gate in report["gates"])
