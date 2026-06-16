from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.pilot_gap_report import build_report, write_artifacts  # noqa: E402
from scripts.readiness_bundle import build_bundle  # noqa: E402


def test_local_pilot_gap_report_lists_next_phase_blockers() -> None:
    report = build_report("local")

    assert report["target"] == "local"
    assert report["ready_for_requested_target"] is True
    assert report["gap_count"] > 0
    assert any(gap["target"] == "ai-demo" for gap in report["blocking_gaps"])
    assert any(gap["owner"] == "engineering" for gap in report["blocking_gaps"])
    assert any(command["name"] == "ai_summary_eval" for command in report["recommended_commands"])
    assert any(item["area"] == "live_data" for item in report["roadmap_items"])


def test_pilot_gap_report_reuses_readiness_bundle() -> None:
    bundle = build_bundle("pilot")

    report = build_report("pilot", bundle=bundle)

    pilot_target = next(target for target in report["activation_targets"] if target["target"] == "pilot")
    assert report["ready_for_requested_target"] is False
    assert report["requested_target_blocker_count"] == pilot_target["blocker_count"]
    assert any(command["name"] == "live_data_contracts" for command in report["recommended_commands"])
    assert any(command["name"] == "unity_audit_smoke" for command in report["recommended_commands"])


def test_pilot_gap_report_writes_json_and_markdown(tmp_path: Path) -> None:
    report = build_report("local")

    write_artifacts(report, tmp_path)

    assert json.loads((tmp_path / "pilot_gap_report.json").read_text(encoding="utf-8"))["target"] == "local"
    markdown = (tmp_path / "pilot_gap_report.md").read_text(encoding="utf-8")
    assert markdown.startswith("# Pilot Gap Report")
    assert "## Blocking Gaps" in markdown
    assert "## Recommended Commands" in markdown
