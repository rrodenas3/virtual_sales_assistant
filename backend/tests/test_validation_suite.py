import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validation_suite import build_suite, write_artifacts  # noqa: E402


def test_validation_suite_combines_local_handoff_and_commands() -> None:
    suite = build_suite("local", run_public_safety=False)

    assert suite["target"] == "local"
    assert suite["passed"] is True
    assert suite["public_safety_ran"] is False
    assert suite["local_handoff"]["passed"] is True
    check_names = {check["name"] for check in suite["checks"]}
    assert {
        "api_contract",
        "demo_seed",
        "final_api_smoke",
        "local_dev_smoke",
        "readiness_bundle",
        "public_safety_scan",
    } <= check_names
    assert any(command["name"] == "local_dev_smoke" for command in suite["runtime_validation_commands"])
    assert suite["activation_targets"][0]["target"] == "local"


def test_validation_suite_writes_nested_artifacts(tmp_path: Path) -> None:
    suite = build_suite("local", run_public_safety=False)

    write_artifacts(suite, tmp_path)

    assert json.loads((tmp_path / "validation_suite.json").read_text(encoding="utf-8"))["passed"] is True
    markdown = (tmp_path / "validation_suite.md").read_text(encoding="utf-8")
    assert markdown.startswith("# Validation Suite")
    assert "## Runtime Validation Commands" in markdown
    assert "local_dev_smoke" in markdown
    assert (tmp_path / "local-handoff" / "local_handoff.json").exists()
    assert (tmp_path / "local-handoff" / "readiness-bundle" / "readiness_bundle.json").exists()
