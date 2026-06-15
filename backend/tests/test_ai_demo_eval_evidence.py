from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.ai_demo_eval_evidence import build_evidence, evidence_from_eval_result, write_artifacts  # noqa: E402


def _eval_result(provider: str = "anthropic", passed: bool = True) -> dict:
    return {
        "passed": passed,
        "failures": [],
        "summary": {
            "providers": [provider],
            "models": ["claude-haiku-4-5"],
            "p95_latency_ms": 1200,
            "trace_completeness": 1.0,
            "max_estimated_cost_eur": 0.012,
        },
    }


def test_evidence_from_eval_result_builds_env_values() -> None:
    evidence = evidence_from_eval_result(_eval_result(), validated_at="2026-06-15T10:00:00Z")

    assert evidence["valid"] is True
    assert evidence["env"]["AI_DEMO_EVAL_VALIDATED"] is True
    assert evidence["env"]["AI_DEMO_EVAL_LAST_VALIDATION_AT"] == "2026-06-15T10:00:00Z"
    assert "provider=anthropic" in evidence["env"]["AI_DEMO_EVAL_VALIDATION_SUMMARY"]
    assert "claude-haiku-4-5" in evidence["env"]["AI_DEMO_EVAL_VALIDATION_SUMMARY"]


def test_evidence_from_eval_result_blocks_template_only_eval() -> None:
    evidence = evidence_from_eval_result(_eval_result(provider="template"), validated_at="2026-06-15T10:00:00Z")

    assert evidence["valid"] is False
    assert evidence["env"]["AI_DEMO_EVAL_VALIDATED"] is False
    assert evidence["blockers"] == ["provider=anthropic not present"]


def test_build_evidence_reads_eval_artifact(tmp_path: Path) -> None:
    (tmp_path / "osa_eval_results.json").write_text(
        """
        {
          "passed": true,
          "summary": {
            "providers": ["anthropic"],
            "models": ["claude-haiku-4-5"],
            "p95_latency_ms": 950,
            "trace_completeness": 1.0,
            "max_estimated_cost_eur": 0.01
          }
        }
        """,
        encoding="utf-8",
    )

    evidence = build_evidence(tmp_path, validated_at="2026-06-15T10:00:00Z")

    assert evidence["valid"] is True
    assert evidence["providers"] == ["anthropic"]


def test_write_artifacts_outputs_env_snippet(tmp_path: Path) -> None:
    evidence = evidence_from_eval_result(_eval_result(), validated_at="2026-06-15T10:00:00Z")

    write_artifacts(evidence, tmp_path)

    assert (tmp_path / "ai_demo_eval_evidence.json").exists()
    assert (tmp_path / "ai_demo_eval_env.json").exists()
    snippet = (tmp_path / "ai_demo_eval.env.snippet").read_text(encoding="utf-8")
    assert "AI_DEMO_EVAL_VALIDATED=true" in snippet
    assert "AI_DEMO_EVAL_LAST_VALIDATION_AT=2026-06-15T10:00:00Z" in snippet
    assert "provider=anthropic" in (tmp_path / "ai_demo_eval_evidence.md").read_text(encoding="utf-8")
