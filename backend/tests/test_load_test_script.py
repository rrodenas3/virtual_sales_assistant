import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.load_test import build_report, percentile, write_artifacts  # noqa: E402


def test_load_test_report_enforces_p95_and_status_budget() -> None:
    passing = build_report(
        latencies_ms=[10, 20, 30, 40, 50],
        status_codes=[200, 200, 200, 200, 200],
        threshold_ms=50,
        base_url="http://localhost:8000",
    )
    assert passing["passed"] is True
    assert passing["p95_ms"] == 50
    assert passing["status_codes"] == {"200": 5}

    failing = build_report(
        latencies_ms=[10, 20, 6000],
        status_codes=[200, 500, 200],
        threshold_ms=5000,
        base_url="http://localhost:8000",
    )
    assert failing["passed"] is False
    assert failing["error_count"] == 1


def test_percentile_handles_empty_and_bounds() -> None:
    assert percentile([], 0.95) == 0.0
    assert percentile([3, 1, 2], 0.0) == 1
    assert percentile([3, 1, 2], 1.0) == 3


def test_load_test_writes_artifacts(tmp_path) -> None:
    report = build_report(
        latencies_ms=[10, 20, 30],
        status_codes=[200, 200, 200],
        threshold_ms=5000,
        base_url="http://localhost:8000",
    )

    write_artifacts(report, tmp_path)

    assert json.loads((tmp_path / "load_test_report.json").read_text(encoding="utf-8"))["passed"] is True
    assert "P95" in (tmp_path / "load_test_report.md").read_text(encoding="utf-8")
