import json

from tests.eval.run_eval import run_eval, write_artifacts


def test_local_eval_harness_passes() -> None:
    result = run_eval()
    assert result["passed"], result
    assert result["summary"]["p95_latency_ms"] <= result["summary"]["thresholds"]["max_p95_latency_ms"]
    assert result["summary"]["hallucination_rate"] == 0.0
    assert result["summary"]["trace_completeness"] == 1.0
    assert result["summary"]["max_estimated_cost_eur"] <= result["summary"]["thresholds"]["max_cost_eur"]
    assert result["summary"]["providers"] == ["template"]
    assert result["summary"]["required_provider"] is None


def test_eval_harness_can_require_ai_provider() -> None:
    result = run_eval(require_provider="anthropic")
    assert not result["passed"]
    assert "aggregate:required_provider_present" in result["failures"]
    assert result["summary"]["required_provider"] == "anthropic"


def test_eval_harness_writes_json_and_csv_artifacts(tmp_path) -> None:
    result = run_eval()

    write_artifacts(result, tmp_path)

    json_path = tmp_path / "osa_eval_results.json"
    csv_path = tmp_path / "osa_eval_results.csv"
    assert json_path.exists()
    assert csv_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"]["trace_completeness"] == 1.0
    assert "summary_provider" in csv_path.read_text(encoding="utf-8")
