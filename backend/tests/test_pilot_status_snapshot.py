from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.pilot_status_snapshot import build_snapshot, write_artifacts  # noqa: E402


def test_local_pilot_status_snapshot_summarizes_handoff_state() -> None:
    snapshot = build_snapshot("local")

    assert snapshot["target"] == "local"
    assert snapshot["passed"] is True
    assert snapshot["summary"]["api_contract_valid"] is True
    assert snapshot["summary"]["required_route_count"] >= 35
    assert snapshot["summary"]["mcp_server_count"] == 7
    assert any(target["target"] == "ai-demo" and target["blocker_count"] > 0 for target in snapshot["activation_targets"])
    assert any(command["name"] == "local_verification" for command in snapshot["runtime_commands"])
    assert snapshot["evidence"]["sections"][0]["name"] == "local_scaffold"
    assert snapshot["manual_checks"]


def test_pilot_status_snapshot_writes_json_and_markdown(tmp_path: Path) -> None:
    snapshot = build_snapshot("local")

    write_artifacts(snapshot, tmp_path)

    assert json.loads((tmp_path / "pilot_status_snapshot.json").read_text(encoding="utf-8"))["passed"] is True
    markdown = (tmp_path / "pilot_status_snapshot.md").read_text(encoding="utf-8")
    assert markdown.startswith("# Pilot Status Snapshot")
    assert "## Activation Targets" in markdown
    assert "local_verification" in markdown
    assert "## Evidence" in markdown
