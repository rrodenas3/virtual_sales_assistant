import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.readme_contract_guard import build_report, write_artifacts  # noqa: E402


def test_readme_contract_guard_passes_for_current_architecture() -> None:
    report = build_report()

    assert report["passed"] is True
    assert {check["name"] for check in report["checks"]} == {
        "linked_targets_exist",
        "required_readme_snippets",
        "route_claims_not_stale",
    }


def test_readme_contract_guard_writes_artifacts(tmp_path: Path) -> None:
    report = build_report()

    write_artifacts(report, tmp_path)

    assert json.loads((tmp_path / "readme_contract_guard.json").read_text(encoding="utf-8"))["passed"] is True
    markdown = (tmp_path / "readme_contract_guard.md").read_text(encoding="utf-8")
    assert markdown.startswith("# README Contract Guard")
    assert "required_readme_snippets" in markdown
