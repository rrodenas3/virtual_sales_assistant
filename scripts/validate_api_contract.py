from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from backend.main import app  # noqa: E402


REQUIRED_ROUTES = {
    "GET /api/v1/health",
    "GET /api/v1/integrations/readiness",
    "GET /api/v1/manager/territory-summary?territory_code=WEST-01",
    "GET /api/v1/manager/approval-queue?territory_code=WEST-01",
    "GET /api/v1/manager/tasks?territory_code=WEST-01&status=OPEN",
    "GET /api/v1/manager/my-tasks?status=OPEN",
    "POST /api/v1/manager/tasks",
    "POST /api/v1/manager/tasks/{task_id}/status",
    "POST /api/v1/agent/osa-summary",
    "POST /api/v1/agent/run",
}


def build_local_contract() -> dict[str, Any]:
    routes = sorted(_openapi_route_signatures(app.openapi()))
    return _contract_from_routes(routes, source="local_app")


def build_remote_contract(base_url: str) -> dict[str, Any]:
    request = Request(f"{base_url.rstrip('/')}/api/v1", headers={"accept": "application/json"})
    try:
        with urlopen(request, timeout=8) as response:  # noqa: S310 - local/operator-provided health URL.
            payload = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise SystemExit(f"Could not read API index from {base_url}: {exc}") from exc
    routes = sorted(str(route) for route in payload.get("routes", []))
    return _contract_from_routes(routes, source=base_url)


def write_artifacts(contract: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "api_contract_report.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# API Contract Report",
        "",
        f"- Source: `{contract['source']}`",
        f"- Valid: `{contract['valid']}`",
        f"- Route count: `{contract['route_count']}`",
        f"- Missing required routes: `{', '.join(contract['missing_required_routes']) or 'none'}`",
        f"- Missing required query params: `{', '.join(contract['missing_required_query_params']) or 'none'}`",
        "",
        "## Required Routes",
        "",
    ]
    lines.extend(f"- `{route}`" for route in contract["required_routes"])
    lines.extend(
        [
            "",
            "## Available Routes",
            "",
        ]
    )
    lines.extend(f"- `{route}`" for route in contract.get("available_routes", []))
    if not contract["valid"]:
        lines.extend(
            [
                "",
                "## Failure Detail",
                "",
                "These route signatures are generated from the public OpenAPI schema for local validation, "
                "and from `/api/v1` for remote validation.",
                "",
            ]
        )
        if contract["missing_required_routes"]:
            lines.append("### Missing Routes")
            lines.extend(f"- `{route}`" for route in contract["missing_required_routes"])
            lines.append("")
        if contract["missing_required_query_params"]:
            lines.append("### Missing Query Params")
            lines.extend(f"- `{param}`" for param in contract["missing_required_query_params"])
            lines.append("")
    (output_dir / "api_contract_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _contract_from_routes(routes: list[str], source: str) -> dict[str, Any]:
    normalized_routes = {_normalize_route(route) for route in routes}
    missing = sorted(route for route in REQUIRED_ROUTES if _normalize_route(route) not in normalized_routes)
    available_query_params = _query_params_by_route(routes)
    missing_query_params = sorted(
        f"{_normalize_route(route)}?{param}"
        for route in REQUIRED_ROUTES
        for param in _query_param_names(route)
        if param not in available_query_params.get(_normalize_route(route), set())
    )
    return {
        "valid": not missing and not missing_query_params,
        "source": source,
        "route_count": len(routes),
        "available_routes": routes,
        "required_routes": sorted(REQUIRED_ROUTES),
        "missing_required_routes": missing,
        "missing_required_query_params": missing_query_params,
    }


def _openapi_route_signatures(schema: dict[str, Any]) -> list[str]:
    signatures: list[str] = []
    for path, path_item in schema.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            query_params = sorted(
                str(param.get("name"))
                for param in operation.get("parameters", [])
                if isinstance(param, dict) and param.get("in") == "query" and param.get("name")
            )
            query = f"?{'&'.join(query_params)}" if query_params else ""
            signatures.append(f"{method.upper()} {path}{query}")
    return signatures


def _normalize_route(route: str) -> str:
    method, _, path = route.partition(" ")
    path = path.split("?", 1)[0]
    return f"{method} {path}"


def _query_param_names(route: str) -> set[str]:
    _, _, path = route.partition(" ")
    _, separator, query = path.partition("?")
    if not separator:
        return set()
    names = set()
    for pair in query.split("&"):
        name, _, _ = pair.partition("=")
        if name:
            names.add(name)
    return names


def _query_params_by_route(routes: list[str]) -> dict[str, set[str]]:
    params: dict[str, set[str]] = {}
    for route in routes:
        params.setdefault(_normalize_route(route), set()).update(_query_param_names(route))
    return params


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the PHANTOM API route contract.")
    parser.add_argument("--base-url", default=None, help="Optional running backend URL, for example http://localhost:8000.")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    contract = build_remote_contract(args.base_url) if args.base_url else build_local_contract()
    if args.output_dir:
        write_artifacts(contract, args.output_dir)
    print(json.dumps(contract, indent=2, sort_keys=True))
    if not contract["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
