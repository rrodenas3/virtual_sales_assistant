from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.log_eval_to_mlflow import build_handoff, write_handoff  # noqa: E402


def _write_eval_artifacts(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "osa_eval_results.json").write_text('{"passed": true}', encoding="utf-8")
    (path / "osa_eval_results.csv").write_text("name,passed\ncase,true\n", encoding="utf-8")
    (path / "mlflow_metrics.json").write_text('{"trace_completeness": 1.0}', encoding="utf-8")
    (path / "mlflow_params.json").write_text('{"providers": "template"}', encoding="utf-8")


def test_build_handoff_validates_complete_eval_artifacts(tmp_path: Path) -> None:
    _write_eval_artifacts(tmp_path)

    handoff = build_handoff(tmp_path, "phantom-vsa-evals", "osa-summary-eval")

    assert handoff["ready"] is True
    assert handoff["experiment_name"] == "phantom-vsa-evals"
    assert handoff["run_name"] == "osa-summary-eval"
    assert handoff["metrics"]["trace_completeness"] == 1.0
    assert handoff["params"]["providers"] == "template"
    assert handoff["missing_artifacts"] == []
    assert all(artifact["exists"] for artifact in handoff["artifacts"])


def test_build_handoff_reports_missing_artifacts(tmp_path: Path) -> None:
    _write_eval_artifacts(tmp_path)
    (tmp_path / "osa_eval_results.csv").unlink()

    handoff = build_handoff(tmp_path, "phantom-vsa-evals", "osa-summary-eval")

    assert handoff["ready"] is False
    assert handoff["missing_artifacts"] == ["osa_eval_results.csv"]


def test_write_handoff_outputs_json_and_markdown(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "eval"
    output_dir = tmp_path / "handoff"
    _write_eval_artifacts(artifact_dir)
    handoff = build_handoff(artifact_dir, "phantom-vsa-evals", "osa-summary-eval")

    write_handoff(handoff, output_dir)

    assert (output_dir / "mlflow_handoff.json").exists()
    markdown = (output_dir / "mlflow_handoff.md").read_text(encoding="utf-8")
    assert "status: ready" in markdown
    assert "experiment: phantom-vsa-evals" in markdown
