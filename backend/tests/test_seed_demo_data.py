import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.seed_demo_data import build_demo_seed, validate_manifest, write_artifacts  # noqa: E402


def test_demo_seed_matches_phase_one_contract() -> None:
    seed = build_demo_seed()
    manifest = seed["manifest"]

    assert validate_manifest(manifest) == []
    assert manifest["territories"] == ["WEST-01"]
    assert manifest["reps"] == ["REP-001", "REP-002", "REP-003", "REP-004", "REP-005"]
    assert manifest["store_count"] == 25
    assert manifest["alert_count"] == 125
    assert manifest["alerts_per_store_min"] == 5
    assert manifest["alerts_per_store_max"] == 5
    assert len({alert["alert_id"] for alert in seed["alerts"]}) == 125
    assert seed["alerts"][0]["alert_id"].count(":") == 2


def test_demo_seed_writes_public_safe_artifacts(tmp_path: Path) -> None:
    seed = build_demo_seed()

    write_artifacts(seed, tmp_path)

    manifest = json.loads((tmp_path / "demo_seed_manifest.json").read_text(encoding="utf-8"))
    assert manifest["public_safe"] is True
    assert json.loads((tmp_path / "store_master_seed.json").read_text(encoding="utf-8"))[0]["store_id"] == "ST-001"
    assert json.loads((tmp_path / "oos_alert_seed.json").read_text(encoding="utf-8"))[0]["alert_id"].startswith("ST-001:")
    markdown = (tmp_path / "demo_seed_manifest.md").read_text(encoding="utf-8")
    assert markdown.startswith("# Demo Seed Manifest")
    assert "REP-005" in markdown
