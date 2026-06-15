from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Log PHANTOM eval artifacts to MLflow when MLflow is installed.")
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--experiment-name", default="phantom-vsa-evals")
    parser.add_argument("--run-name", default="osa-summary-eval")
    args = parser.parse_args()

    try:
        import mlflow
    except ImportError as exc:
        raise SystemExit("MLflow is not installed. Install mlflow in the evaluation environment to use this script.") from exc

    metrics = json.loads((args.artifact_dir / "mlflow_metrics.json").read_text(encoding="utf-8"))
    params = json.loads((args.artifact_dir / "mlflow_params.json").read_text(encoding="utf-8"))

    mlflow.set_experiment(args.experiment_name)
    with mlflow.start_run(run_name=args.run_name):
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        for artifact in [
            "osa_eval_results.json",
            "osa_eval_results.csv",
            "mlflow_metrics.json",
            "mlflow_params.json",
        ]:
            path = args.artifact_dir / artifact
            if path.exists():
                mlflow.log_artifact(str(path))


if __name__ == "__main__":
    main()
