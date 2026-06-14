from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from backend.main import app

DATASET = Path(__file__).with_name("osa_eval_dataset.json")
SKU_PATTERN = re.compile(r"Core SKU \d+")


def _token(rep_id: str, territory_code: str, role: str = "rep") -> str:
    def enc(data: dict) -> str:
        raw = json.dumps(data, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{enc({'alg': 'none', 'typ': 'JWT'})}.{enc({'sub': rep_id, 'territory_code': territory_code, 'role': role})}."


def _client(rep_id: str, territory_code: str) -> TestClient:
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {_token(rep_id, territory_code)}"})
    return client


def run_eval() -> dict[str, Any]:
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

            checks = {
                "visit_priority_status": visits.status_code == 200,
                "visit_priority_audited": bool(visits.json()[0].get("audit_event_ids")) if visits.status_code == 200 else False,
                "unauthorized_store_hidden": unauthorized.status_code == 404,
                "summary_status": summary_response.status_code == 200,
                "summary_grounded_ids": set(summary_body.get("grounded_alert_ids", [])) == set(alert_ids),
                "summary_no_hallucinated_skus": not hallucinated_skus,
                "summary_audited": bool(summary_body.get("audit_event_id")),
                "summary_latency_budget": latency_ms <= case["latency_budget_ms"],
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
                }
            )

    return {"passed": not failures, "failures": failures, "results": results}


def main() -> None:
    result = run_eval()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
