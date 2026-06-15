import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.guardrail_classifier_smoke import build_smoke, write_artifacts  # noqa: E402


def test_guardrail_classifier_smoke_validates_threshold_and_fallback() -> None:
    report = build_smoke()

    assert report["valid"] is True
    assert report["checks"]["allow_below_threshold"] is True
    assert report["checks"]["block_at_threshold"] is True
    assert report["checks"]["fallback_pattern_block"] is True
    assert report["checks"]["classifier_payload_minimal"] is True


def test_guardrail_classifier_smoke_writes_handoff_artifacts(tmp_path: Path) -> None:
    report = build_smoke()

    write_artifacts(report, tmp_path)

    assert json.loads((tmp_path / "guardrail_classifier_smoke.json").read_text(encoding="utf-8"))["valid"] is True
    markdown = (tmp_path / "guardrail_classifier_smoke.md").read_text(encoding="utf-8")
    assert markdown.startswith("# Guardrail Classifier Smoke")
    assert "block_at_threshold" in markdown
