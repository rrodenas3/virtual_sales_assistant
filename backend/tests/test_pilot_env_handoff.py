import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.pilot_env_handoff import build_handoff, write_artifacts  # noqa: E402


def _write_sources(path: Path) -> tuple[Path, Path]:
    ai_path = path / "ai_demo_eval_env.json"
    live_path = path / "readiness_env.json"
    ai_path.write_text(
        json.dumps(
            {
                "AI_DEMO_EVAL_VALIDATED": True,
                "AI_DEMO_EVAL_LAST_VALIDATION_AT": "2026-06-15T10:00:00Z",
                "AI_DEMO_EVAL_VALIDATION_SUMMARY": "provider=anthropic; p95_ms=1200",
            }
        ),
        encoding="utf-8",
    )
    live_path.write_text(
        json.dumps(
            {
                "LIVE_DATA_CONTRACT_VALIDATED": True,
                "LIVE_DATA_CONTRACT_LAST_VALIDATION_AT": "2026-06-15T11:00:00Z",
                "LIVE_DATA_CONTRACT_VALIDATION_SUMMARY": "2/2 contracts valid; rows=51",
            }
        ),
        encoding="utf-8",
    )
    return ai_path, live_path


def test_build_handoff_merges_public_safe_validation_keys(tmp_path: Path) -> None:
    ai_path, live_path = _write_sources(tmp_path)

    handoff = build_handoff(ai_path, live_path)

    assert handoff["ready"] is True
    assert handoff["missing_sources"] == []
    assert handoff["missing_keys"] == []
    assert handoff["env"]["AI_DEMO_EVAL_VALIDATED"] is True
    assert handoff["env"]["LIVE_DATA_CONTRACT_VALIDATED"] is True


def test_build_handoff_reports_missing_sources(tmp_path: Path) -> None:
    ai_path, _live_path = _write_sources(tmp_path)

    handoff = build_handoff(ai_path, tmp_path / "missing.json")

    assert handoff["ready"] is False
    assert handoff["missing_sources"] == ["live_data"]
    assert "LIVE_DATA_CONTRACT_VALIDATED" in handoff["missing_keys"]


def test_write_artifacts_outputs_env_snippet(tmp_path: Path) -> None:
    ai_path, live_path = _write_sources(tmp_path)
    output_dir = tmp_path / "out"
    handoff = build_handoff(ai_path, live_path)

    write_artifacts(handoff, output_dir)

    assert (output_dir / "pilot_env_handoff.json").exists()
    snippet = (output_dir / "pilot_validation.env.snippet").read_text(encoding="utf-8")
    assert "AI_DEMO_EVAL_VALIDATED=true" in snippet
    assert "LIVE_DATA_CONTRACT_VALIDATED=true" in snippet
    assert "provider=anthropic" in (output_dir / "pilot_env_handoff.md").read_text(encoding="utf-8")
