from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from backend.adapters.crm import ExternalCRMAdapter  # noqa: E402
from backend.adapters.erp import ExternalERPAdapter  # noqa: E402
from backend.config import Settings  # noqa: E402
from backend.services.hashing import stable_payload_hash  # noqa: E402


async def build_smoke() -> dict[str, Any]:
    requests: list[dict[str, Any]] = []
    config = Settings(
        crm_endpoint="https://crm.example.test",
        crm_token_ref="approved-token-reference",
        erp_endpoint="https://erp.example.test",
        erp_token_ref="approved-token-reference",
    )

    real_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8")) if request.content else {}
        requests.append(
            {
                "method": request.method,
                "path": request.url.path,
                "auth_header_present": bool(request.headers.get("authorization")),
                "payload": body,
            }
        )
        if request.url.path.endswith("/visit-logs"):
            return httpx.Response(200, json={"external_id": "visit-smoke-1", "status": "SUBMITTED"})
        if request.url.path.endswith("/orders"):
            return httpx.Response(200, json={"erp_order_id": "ERP-SMOKE-1", "status": "ACCEPTED"})
        return httpx.Response(404, json={"detail": "unexpected path"})

    transport = httpx.MockTransport(handler)

    def client_factory(*, timeout: float) -> httpx.AsyncClient:
        return real_client(transport=transport, timeout=timeout)

    original_client = httpx.AsyncClient
    httpx.AsyncClient = client_factory  # type: ignore[assignment]
    try:
        crm_payload = {
            "store_id": "ST-001",
            "rep_id": "REP-001",
            "session_id": "action-smoke-session",
            "notes": "External action provider dry run",
            "outcome": "completed",
        }
        crm_result = await ExternalCRMAdapter(config).submit_visit_log(crm_payload)
        order_payload = {
            "store_id": "ST-001",
            "rep_id": "REP-001",
            "items": [
                {
                    "sku_id": "SKU-4001",
                    "sku_name": "Core SKU 4001",
                    "quantity": 12,
                    "reason": "High grounded OOS risk",
                }
            ],
            "notes": "External ERP dry run",
        }
        payload_hash = stable_payload_hash(order_payload)
        erp_result = await ExternalERPAdapter(config).submit_order(
            draft_id="draft-smoke-1",
            payload=order_payload,
            approval_id="approval-smoke-1",
            payload_hash=payload_hash,
        )
    finally:
        httpx.AsyncClient = original_client  # type: ignore[assignment]

    crm_request = next(item for item in requests if item["path"].endswith("/visit-logs"))
    erp_request = next(item for item in requests if item["path"].endswith("/orders"))
    checks = {
        "crm_status_submitted": crm_result.status == "SUBMITTED",
        "crm_auth_header_present": crm_request["auth_header_present"],
        "crm_payload_scoped": crm_request["payload"].get("store_id") == "ST-001"
        and crm_request["payload"].get("rep_id") == "REP-001",
        "erp_status_accepted": erp_result.status == "ACCEPTED",
        "erp_auth_header_present": erp_request["auth_header_present"],
        "erp_payload_hash_bound": erp_request["payload"].get("payload_hash") == payload_hash,
        "erp_approval_id_bound": erp_request["payload"].get("approval_id") == "approval-smoke-1",
    }
    return {
        "valid": all(checks.values()),
        "dry_run_only": True,
        "checks": checks,
        "requests": [
            _redact_request(crm_request),
            _redact_request(erp_request),
        ],
        "results": {
            "crm_external_id": crm_result.external_id,
            "crm_status": crm_result.status,
            "erp_order_id": erp_result.erp_order_id,
            "erp_status": erp_result.status,
        },
    }


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "action_provider_smoke.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Action Provider Smoke",
        "",
        f"- Valid: `{report['valid']}`",
        f"- Dry run only: `{report['dry_run_only']}`",
        "",
        "| Check | Status |",
        "|---|---:|",
    ]
    lines.extend(f"| {name} | {'pass' if passed else 'fail'} |" for name, passed in report["checks"].items())
    lines.extend(["", "## Requests", ""])
    for request in report["requests"]:
        lines.append(f"- `{request['method']} {request['path']}` payload keys: `{', '.join(request['payload_keys'])}`")
    (output_dir / "action_provider_smoke.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _redact_request(request: dict[str, Any]) -> dict[str, Any]:
    payload = dict(request["payload"])
    return {
        "method": request["method"],
        "path": request["path"],
        "auth_header_present": request["auth_header_present"],
        "payload_keys": sorted(payload),
        "payload": payload,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a dry-run CRM/ERP action provider smoke artifact.")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/action-provider-smoke"))
    args = parser.parse_args()

    report = asyncio.run(build_smoke())
    write_artifacts(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
