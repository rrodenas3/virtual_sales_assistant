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

from backend.config import settings  # noqa: E402
from backend.memory import adapters  # noqa: E402
from backend.memory.adapters import Mem0Adapter, NullMemoryAdapter, memory_status  # noqa: E402


async def build_smoke() -> dict[str, Any]:
    original = {
        "memory_provider": settings.memory_provider,
        "mem0_token_ref": settings.mem0_token_ref,
        "mem0_endpoint": settings.mem0_endpoint,
        "discovery_memory_retention_policy": settings.discovery_memory_retention_policy,
        "discovery_memory_scopes": settings.discovery_memory_scopes,
    }
    original_client = adapters.httpx.AsyncClient
    requests: list[dict[str, Any]] = []
    responses = [
        {"memories": [{"id": "mem-smoke-1", "memory": "Store ST-001 has repeated shelf gaps."}]},
        {"id": "write-smoke-1"},
    ]

    real_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8")) if request.content else {}
        requests.append(
            {
                "method": request.method,
                "path": request.url.path,
                "auth_header_present": bool(request.headers.get("authorization")),
                "payload": payload,
            }
        )
        return httpx.Response(200, json=responses.pop(0))

    transport = httpx.MockTransport(handler)

    def client_factory(*, timeout: float) -> httpx.AsyncClient:
        return real_client(transport=transport, timeout=timeout)

    try:
        settings.memory_provider = "none"
        disabled_adapter = NullMemoryAdapter()
        disabled_context = await disabled_adapter.get_context(rep_id="REP-001", store_id="ST-001")

        settings.memory_provider = "mem0"
        settings.mem0_token_ref = "approved-token-reference"
        settings.mem0_endpoint = "https://mem0.example.test"
        settings.discovery_memory_retention_policy = "30 days"
        settings.discovery_memory_scopes = "rep,store,session"
        adapters.httpx.AsyncClient = client_factory  # type: ignore[assignment]
        adapter = Mem0Adapter()
        context = await adapter.get_context(rep_id="REP-001", store_id="ST-001")
        await adapter.record_interaction(
            rep_id="REP-001",
            session_id="memory-smoke-session",
            payload={
                "event_type": "osa_summary_created",
                "store_id": "ST-001",
                "summary": "Grounded summary for memory smoke.",
            },
        )
        ready_status = memory_status()
    finally:
        for key, value in original.items():
            setattr(settings, key, value)
        adapters.httpx.AsyncClient = original_client  # type: ignore[assignment]

    search_request = next(item for item in requests if item["path"].endswith("/memories/search"))
    write_request = next(item for item in requests if item["path"].endswith("/memories"))
    checks = {
        "disabled_default_has_no_memory": disabled_context["provider"] == "none" and disabled_context["memories"] == [],
        "mem0_status_ready_with_discovery": ready_status["ready"] is True,
        "search_scoped_to_rep_store": search_request["payload"].get("user_id") == "REP-001"
        and search_request["payload"].get("filters", {}).get("store_id") == "ST-001",
        "write_scoped_to_session_store": write_request["payload"].get("user_id") == "REP-001"
        and write_request["payload"].get("metadata", {}).get("session_id") == "memory-smoke-session"
        and write_request["payload"].get("metadata", {}).get("store_id") == "ST-001",
        "auth_headers_present": all(item["auth_header_present"] for item in requests),
        "context_returns_memory": context["provider"] == "mem0" and len(context["memories"]) == 1,
    }
    return {
        "valid": all(checks.values()),
        "dry_run_only": True,
        "checks": checks,
        "requests": [_redact_request(item) for item in requests],
        "memory_count": len(context["memories"]),
    }


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "memory_provider_smoke.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# Memory Provider Smoke",
        "",
        f"- Valid: `{report['valid']}`",
        f"- Dry run only: `{report['dry_run_only']}`",
        f"- Memory count: `{report['memory_count']}`",
        "",
        "| Check | Status |",
        "|---|---:|",
    ]
    lines.extend(f"| {name} | {'pass' if passed else 'fail'} |" for name, passed in report["checks"].items())
    (output_dir / "memory_provider_smoke.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _redact_request(request: dict[str, Any]) -> dict[str, Any]:
    payload = dict(request["payload"])
    return {
        "method": request["method"],
        "path": request["path"],
        "auth_header_present": request["auth_header_present"],
        "payload_keys": sorted(payload),
        "metadata_keys": sorted(payload.get("metadata", {})) if isinstance(payload.get("metadata"), dict) else [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a dry-run memory provider smoke artifact.")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/memory-provider-smoke"))
    args = parser.parse_args()

    report = asyncio.run(build_smoke())
    write_artifacts(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
