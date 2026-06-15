from __future__ import annotations

import base64
import argparse
import csv
import json
import re
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from backend.main import app

DATASET = Path(__file__).with_name("osa_eval_dataset.json")
SKU_PATTERN = re.compile(r"Core SKU \d+")
MAX_COST_EUR = 0.08
MAX_HALLUCINATION_RATE = 0.0
MIN_TRACE_COMPLETENESS = 1.0
MAX_P95_LATENCY_MS = 5000


def _token(rep_id: str, territory_code: str, role: str = "rep") -> str:
    def enc(data: dict) -> str:
        raw = json.dumps(data, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{enc({'alg': 'none', 'typ': 'JWT'})}.{enc({'sub': rep_id, 'territory_code': territory_code, 'role': role})}."


def _client(rep_id: str, territory_code: str) -> TestClient:
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {_token(rep_id, territory_code)}"})
    return client


def run_eval(*, require_provider: str | None = None) -> dict[str, Any]:
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    failures: list[str] = []

    for case in dataset["cases"]:
        with _client(case["rep_id"], case["territory_code"]) as client:
            visits = client.get(
                f"/api/v1/visits/today?territory_code={case['territory_code']}&date={case['visit_date']}"
            )
            unauthorized = client.get(f"/api/v1/stores/{case['unauthorized_store_id']}")
            alerts_response = client.get(f"/api/v1/stores/{case['store_id']}/alerts?limit=2")
            alerts = alerts_response.json()["alerts"] if alerts_response.status_code == 200 else []
            alert_ids = [alert["alert_id"] for alert in alerts]
            allowed_skus = {alert["sku_name"] for alert in alerts}

            started = time.perf_counter()
            summary_response = client.post(
                "/api/v1/agent/osa-summary",
                json={
                    "territory_code": case["territory_code"],
                    "store_id": case["store_id"],
                    "session_id": f"eval:{case['name']}",
                    "alert_ids": alert_ids,
                },
            )
            latency_ms = round((time.perf_counter() - started) * 1000, 2)

            summary_body = summary_response.json() if summary_response.status_code == 200 else {}
            summary_text = summary_body.get("summary", "")
            named_skus = set(SKU_PATTERN.findall(summary_text))
            hallucinated_skus = sorted(named_skus - allowed_skus)
            audit_response = client.get(f"/api/v1/audit/session/eval:{case['name']}")
            audit_events = audit_response.json().get("events", []) if audit_response.status_code == 200 else []
            summary_audit_events = [event for event in audit_events if event["event_type"] == "osa_summary_created"]
            summary_audit_payload = summary_audit_events[-1]["payload_json"] if summary_audit_events else {}
            cost_eur = float(summary_audit_payload.get("estimated_cost_eur", 0.0))
            provider = summary_audit_payload.get("summary_provider", "unknown")
            model_id = summary_audit_payload.get("model_id", summary_body.get("model_id", "unknown"))
            trace_complete = bool(summary_body.get("audit_event_id")) and bool(summary_audit_events)

            checks = {
                "visit_priority_status": visits.status_code == 200,
                "visit_priority_audited": bool(visits.json()[0].get("audit_event_ids")) if visits.status_code == 200 else False,
                "unauthorized_store_hidden": unauthorized.status_code == 404,
                "summary_status": summary_response.status_code == 200,
                "summary_grounded_ids": set(summary_body.get("grounded_alert_ids", [])) == set(alert_ids),
                "summary_no_hallucinated_skus": not hallucinated_skus,
                "summary_audited": trace_complete,
                "summary_latency_budget": latency_ms <= case["latency_budget_ms"],
                "summary_cost_budget": cost_eur <= MAX_COST_EUR,
                "summary_provider_known": provider in {"template", "anthropic"},
            }
            case_failures = [name for name, passed in checks.items() if not passed]
            if case_failures:
                failures.extend(f"{case['name']}:{name}" for name in case_failures)
            results.append(
                {
                    "name": case["name"],
                    "latency_ms": latency_ms,
                    "checks": checks,
                    "hallucinated_skus": hallucinated_skus,
                    "grounded_alert_count": len(alert_ids),
                    "summary_provider": provider,
                    "model_id": model_id,
                    "estimated_cost_eur": cost_eur,
                    "trace_complete": trace_complete,
                }
            )

    total_cases = len(results)
    hallucinated_cases = len([result for result in results if result["hallucinated_skus"]])
    trace_complete_cases = len([result for result in results if result["trace_complete"]])
    latencies = sorted(float(result["latency_ms"]) for result in results)
    p95_latency_ms = _percentile(latencies, 0.95) if latencies else 0.0
    max_cost_eur = max((float(result["estimated_cost_eur"]) for result in results), default=0.0)
    hallucination_rate = hallucinated_cases / total_cases if total_cases else 0.0
    trace_completeness = trace_complete_cases / total_cases if total_cases else 0.0
    aggregate_checks = {
        "p95_latency_budget": p95_latency_ms <= MAX_P95_LATENCY_MS,
        "hallucination_rate_budget": hallucination_rate <= MAX_HALLUCINATION_RATE,
        "trace_completeness_budget": trace_completeness >= MIN_TRACE_COMPLETENESS,
        "cost_budget": max_cost_eur <= MAX_COST_EUR,
    }
    providers = sorted({str(result["summary_provider"]) for result in results})
    if require_provider:
        aggregate_checks["required_provider_present"] = require_provider in providers
    failures.extend(f"aggregate:{name}" for name, passed in aggregate_checks.items() if not passed)
    summary = {
        "case_count": total_cases,
        "p95_latency_ms": p95_latency_ms,
        "hallucination_rate": hallucination_rate,
        "trace_completeness": trace_completeness,
        "max_estimated_cost_eur": max_cost_eur,
        "providers": providers,
        "models": sorted({str(result["model_id"]) for result in results}),
        "required_provider": require_provider,
        "thresholds": {
            "max_p95_latency_ms": MAX_P95_LATENCY_MS,
            "max_hallucination_rate": MAX_HALLUCINATION_RATE,
            "min_trace_completeness": MIN_TRACE_COMPLETENESS,
            "max_cost_eur": MAX_COST_EUR,
        },
        "checks": aggregate_checks,
    }
    return {"passed": not failures, "failures": failures, "summary": summary, "results": results}


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    index = max(0, min(len(values) - 1, round((len(values) - 1) * percentile)))
    return round(values[index], 2)


def write_artifacts(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "osa_eval_results.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "mlflow_metrics.json").write_text(
        json.dumps(_mlflow_metrics(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "mlflow_params.json").write_text(
        json.dumps(_mlflow_params(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    with (output_dir / "osa_eval_results.csv").open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "name",
                "latency_ms",
                "summary_provider",
                "model_id",
                "estimated_cost_eur",
                "trace_complete",
                "grounded_alert_count",
                "hallucinated_skus",
            ],
        )
        writer.writeheader()
        for row in result["results"]:
            writer.writerow(
                {
                    "name": row["name"],
                    "latency_ms": row["latency_ms"],
                    "summary_provider": row["summary_provider"],
                    "model_id": row["model_id"],
                    "estimated_cost_eur": row["estimated_cost_eur"],
                    "trace_complete": row["trace_complete"],
                    "grounded_alert_count": row["grounded_alert_count"],
                    "hallucinated_skus": ";".join(row["hallucinated_skus"]),
                }
            )


def _mlflow_metrics(result: dict[str, Any]) -> dict[str, float]:
    summary = result["summary"]
    checks = summary["checks"]
    return {
        "case_count": float(summary["case_count"]),
        "p95_latency_ms": float(summary["p95_latency_ms"]),
        "hallucination_rate": float(summary["hallucination_rate"]),
        "trace_completeness": float(summary["trace_completeness"]),
        "max_estimated_cost_eur": float(summary["max_estimated_cost_eur"]),
        "passed": 1.0 if result["passed"] else 0.0,
        **{f"check_{name}": 1.0 if passed else 0.0 for name, passed in checks.items()},
    }


def _mlflow_params(result: dict[str, Any]) -> dict[str, str]:
    summary = result["summary"]
    return {
        "providers": ",".join(summary["providers"]),
        "models": ",".join(summary["models"]),
        "required_provider": str(summary["required_provider"] or ""),
        "threshold_max_p95_latency_ms": str(summary["thresholds"]["max_p95_latency_ms"]),
        "threshold_max_hallucination_rate": str(summary["thresholds"]["max_hallucination_rate"]),
        "threshold_min_trace_completeness": str(summary["thresholds"]["min_trace_completeness"]),
        "threshold_max_cost_eur": str(summary["thresholds"]["max_cost_eur"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PHANTOM local OSA summary eval gates.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Optional directory for JSON/CSV eval artifacts.")
    parser.add_argument(
        "--require-provider",
        choices=["template", "anthropic"],
        default=None,
        help="Fail unless at least one eval case used the required summary provider.",
    )
    args = parser.parse_args()
    result = run_eval(require_provider=args.require_provider)
    if args.output_dir:
        write_artifacts(result, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
