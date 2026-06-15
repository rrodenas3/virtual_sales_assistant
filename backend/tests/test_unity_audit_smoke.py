import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.unity_audit_smoke import build_smoke, write_artifacts  # noqa: E402


@pytest.mark.asyncio
async def test_unity_audit_smoke_builds_parameterized_insert_contract() -> None:
    report = await build_smoke("phantom.audit.agent_actions")

    assert report["valid"] is True
    assert report["dry_run_only"] is True
    assert "INSERT INTO phantom.audit.agent_actions" in report["statement_preview"]
    assert "REP-001" not in report["statement_preview"]
    assert "rep_id" in report["parameter_names"]
    assert report["missing_parameters"] == []
    assert report["ddl"]["append_only"] is True


@pytest.mark.asyncio
async def test_unity_audit_smoke_writes_handoff_artifacts(tmp_path: Path) -> None:
    report = await build_smoke("phantom.audit.agent_actions")

    write_artifacts(report, tmp_path)

    assert json.loads((tmp_path / "unity_audit_smoke.json").read_text(encoding="utf-8"))["valid"] is True
    markdown = (tmp_path / "unity_audit_smoke.md").read_text(encoding="utf-8")
    assert markdown.startswith("# Unity Audit Smoke")
    assert "rep_id" in markdown
