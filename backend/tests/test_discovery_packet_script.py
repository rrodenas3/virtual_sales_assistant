import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.discovery_packet import build_report, write_artifacts  # noqa: E402


def test_discovery_packet_script_builds_public_safe_pilot_packet() -> None:
    report = build_report("pilot")

    assert report["target"] == "pilot"
    assert report["missing_count"] >= 7
    assert report["owner_groups"]
    assert "public_safety_notes" in report
    assert "C:\\Users" not in json.dumps(report)


def test_discovery_packet_script_writes_artifacts(tmp_path: Path) -> None:
    report = build_report("pilot")

    write_artifacts(report, tmp_path)

    payload = json.loads((tmp_path / "discovery_packet.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "discovery_packet.md").read_text(encoding="utf-8")
    assert payload["target"] == "pilot"
    assert markdown.startswith("# Discovery Packet")
    assert "## Owner Groups" in markdown
    assert "discovery_sso_provider" in markdown
