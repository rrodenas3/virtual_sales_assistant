from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

import httpx

MOCK_TOKEN = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJSRVAtMDAxIiwidGVycml0b3J5X2NvZGUiOiJXRVNULTAxIiwicm9sZSI6InJlcCJ9."
DEFAULT_BODY = {"territory_code": "WEST-01", "store_id": "ST-001", "session_id": "load_test", "alert_ids": []}
TOKEN_ENV_VAR = "LOAD_TEST_BEARER_TOKEN"


def load_test_token() -> tuple[str, str]:
    token = os.getenv(TOKEN_ENV_VAR)
    if token:
        return token, "environment"
    return MOCK_TOKEN, "mock"


async def one(client: httpx.AsyncClient, body: dict[str, Any]) -> tuple[float, int]:
    started = time.perf_counter()
    response = await client.post(
        "/api/v1/agent/osa-summary",
        json=body,
    )
    return (time.perf_counter() - started) * 1000, response.status_code


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * pct)))
    return ordered[index]


def build_report(
    *,
    latencies_ms: list[float],
    status_codes: list[int],
    threshold_ms: float,
    base_url: str,
    auth_source: str = "mock",
) -> dict[str, Any]:
    error_count = sum(1 for status in status_codes if status >= 400)
    p95 = percentile(latencies_ms, 0.95)
    return {
        "passed": error_count == 0 and p95 <= threshold_ms,
        "base_url": base_url,
        "auth_source": auth_source,
        "request_count": len(latencies_ms),
        "error_count": error_count,
        "threshold_p95_ms": threshold_ms,
        "p50_ms": round(percentile(latencies_ms, 0.50), 2),
        "p95_ms": round(p95, 2),
        "avg_ms": round(statistics.mean(latencies_ms), 2) if latencies_ms else 0.0,
        "max_ms": round(max(latencies_ms), 2) if latencies_ms else 0.0,
        "status_codes": {str(status): status_codes.count(status) for status in sorted(set(status_codes))},
    }


async def run_load(args: argparse.Namespace) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(args.concurrency)
    token, auth_source = load_test_token()
    async with httpx.AsyncClient(
        base_url=args.base_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=args.timeout_seconds,
    ) as client:

        async def bounded_call() -> tuple[float, int]:
            async with semaphore:
                return await one(client, DEFAULT_BODY)

        results = await asyncio.gather(*(bounded_call() for _ in range(args.requests)))
    latencies = [latency for latency, _ in results]
    status_codes = [status for _, status in results]
    return build_report(
        latencies_ms=latencies,
        status_codes=status_codes,
        threshold_ms=args.threshold_p95_ms,
        base_url=args.base_url,
        auth_source=auth_source,
    )


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "load_test_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Summary Endpoint Load Test",
        "",
        f"- Passed: `{report['passed']}`",
        f"- Auth source: `{report['auth_source']}`",
        f"- Requests: `{report['request_count']}`",
        f"- Errors: `{report['error_count']}`",
        f"- P95: `{report['p95_ms']} ms`",
        f"- Threshold: `{report['threshold_p95_ms']} ms`",
    ]
    (output_dir / "load_test_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description="Load-test the grounded OSA summary endpoint.")
    cli.add_argument("--base-url", default="http://localhost:8000")
    cli.add_argument("--requests", type=int, default=50)
    cli.add_argument("--concurrency", type=int, default=10)
    cli.add_argument("--threshold-p95-ms", type=float, default=5000)
    cli.add_argument("--timeout-seconds", type=float, default=10)
    cli.add_argument("--output-dir", type=Path, default=None)
    return cli


async def async_main() -> dict[str, Any]:
    args = parser().parse_args()
    report = await run_load(args)
    if args.output_dir:
        write_artifacts(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    report = asyncio.run(async_main())
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

