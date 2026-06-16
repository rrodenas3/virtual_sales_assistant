import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.spec_decision_guard import build_report, write_artifacts  # noqa: E402


def test_spec_decision_guard_passes_for_locked_phase1_decisions() -> None:
    report = build_report()

    assert report["passed"] is True
    assert {check["name"] for check in report["checks"]} == {
        "forbidden_dependencies",
        "locked_decision_text",
    }


def test_spec_decision_guard_writes_artifacts(tmp_path: Path) -> None:
    report = build_report()

    write_artifacts(report, tmp_path)

    assert json.loads((tmp_path / "spec_decision_guard.json").read_text(encoding="utf-8"))["passed"] is True
    markdown = (tmp_path / "spec_decision_guard.md").read_text(encoding="utf-8")
    assert markdown.startswith("# Spec Decision Guard")
    assert "forbidden_dependencies" in markdown
