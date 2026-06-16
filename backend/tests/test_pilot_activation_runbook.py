import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.pilot_activation_runbook import build_report, write_artifacts  # noqa: E402


def test_pilot_activation_runbook_report_contains_final_phase_plan() -> None:
    report = build_report("local")

    assert report["current_target"] == "local"
    assert report["phase_count"] == 8
    assert report["ready_phase_count"] >= 1
    phase_ids = {phase["phase_id"] for phase in report["phases"]}
    assert "phase-1-ai-demo" in phase_ids
    assert "phase-6-final-pilot" in phase_ids
    assert report["public_safety_notes"]


def test_pilot_activation_runbook_writes_handoff_artifacts(tmp_path: Path) -> None:
    report = build_report("local")

    write_artifacts(report, tmp_path)

    payload = json.loads((tmp_path / "pilot_activation_runbook.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "pilot_activation_runbook.md").read_text(encoding="utf-8")
    assert payload["phase_count"] == 8
    assert markdown.startswith("# Pilot Activation Runbook")
    assert "Real AI Demo Readiness" in markdown
    assert "Final VSA Pilot Gate" in markdown
    assert "Public Safety" in markdown
