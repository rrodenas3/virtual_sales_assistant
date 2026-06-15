from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EXPECTED_ARTIFACTS = (
    "osa_eval_results.json",
    "osa_eval_results.csv",
    "mlflow_metrics.json",
    "mlflow_params.json",
)


def build_handoff(artifact_dir: Path, experiment_name: str, run_name: str) -> dict[str, Any]:
    metrics_path = artifact_dir / "mlflow_metrics.json"
    params_path = artifact_dir / "mlflow_params.json"
    metrics = _read_json(metrics_path) if metrics_path.exists() else {}
    params = _read_json(params_path) if params_path.exists() else {}
    artifacts = [
        {"name": artifact, "exists": (artifact_dir / artifact).exists()}
        for artifact in EXPECTED_ARTIFACTS
    ]
    missing_artifacts = [artifact["name"] for artifact in artifacts if not artifact["exists"]]
    missing_inputs = [
        name
        for name, value in (("mlflow_metrics.json", metrics), ("mlflow_params.json", params))
        if not value
    ]
    return {
        "ready": not missing_artifacts and not missing_inputs,
        "experiment_name": experiment_name,
        "run_name": run_name,
        "artifact_dir": artifact_dir.as_posix(),
        "metrics": metrics,
        "params": params,
        "artifacts": artifacts,
        "missing_artifacts": missing_artifacts,
        "missing_inputs": missing_inputs,
    }


def write_handoff(handoff: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "mlflow_handoff.json").write_text(
        json.dumps(handoff, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "mlflow_handoff.md").write_text(_handoff_markdown(handoff), encoding="utf-8")


def log_to_mlflow(handoff: dict[str, Any], artifact_dir: Path) -> None:
    if not handoff["ready"]:
        raise SystemExit(f"MLflow handoff is incomplete: {handoff['missing_artifacts'] or handoff['missing_inputs']}")

    try:
        import mlflow
    except ImportError as exc:
        raise SystemExit("MLflow is not installed. Install mlflow in the evaluation environment to use this script.") from exc

    mlflow.set_experiment(handoff["experiment_name"])
    with mlflow.start_run(run_name=handoff["run_name"]):
        mlflow.log_params(handoff["params"])
        mlflow.log_metrics(handoff["metrics"])
        for artifact in EXPECTED_ARTIFACTS:
            mlflow.log_artifact(str(artifact_dir / artifact))


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path.name} must contain a JSON object.")
    return payload


def _handoff_markdown(handoff: dict[str, Any]) -> str:
    status = "ready" if handoff["ready"] else "blocked"
    artifact_lines = [
        f"- {artifact['name']}: {'present' if artifact['exists'] else 'missing'}"
        for artifact in handoff["artifacts"]
    ]
    metric_lines = [f"- {name}: {value}" for name, value in sorted(handoff["metrics"].items())]
    param_lines = [f"- {name}: {value}" for name, value in sorted(handoff["params"].items())]
    return "\n".join(
        [
            "# MLflow Handoff",
            "",
            f"- status: {status}",
            f"- experiment: {handoff['experiment_name']}",
            f"- run: {handoff['run_name']}",
            "",
            "## Artifacts",
            *artifact_lines,
            "",
            "## Metrics",
            *(metric_lines or ["- none"]),
            "",
            "## Params",
            *(param_lines or ["- none"]),
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Log PHANTOM eval artifacts to MLflow when MLflow is installed.")
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--experiment-name", default="phantom-vsa-evals")
    parser.add_argument("--run-name", default="osa-summary-eval")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate eval artifacts and print a handoff manifest without importing MLflow.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional directory for mlflow_handoff.json and mlflow_handoff.md.",
    )
    args = parser.parse_args()

    handoff = build_handoff(args.artifact_dir, args.experiment_name, args.run_name)
    if args.output_dir:
        write_handoff(handoff, args.output_dir)
    if args.dry_run:
        print(json.dumps(handoff, indent=2, sort_keys=True))
        if not handoff["ready"]:
            raise SystemExit(1)
        return

    log_to_mlflow(handoff, args.artifact_dir)


if __name__ == "__main__":
    main()
