from __future__ import annotations

import argparse
import base64
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen


FetchResult = tuple[int, str]
Fetcher = Callable[[str, dict[str, str] | None], FetchResult]


def build_report(
    frontend_url: str = "http://localhost:5173",
    backend_url: str = "http://localhost:8000",
    *,
    fetcher: Fetcher | None = None,
) -> dict[str, Any]:
    fetch = fetcher or _fetch
    frontend = frontend_url.rstrip("/")
    backend = backend_url.rstrip("/")
    checks = [
        _check_frontend_index(fetch, frontend),
        _check_frontend_dev_module(fetch, frontend),
        _check_backend_health(fetch, backend),
        _check_backend_route_data(fetch, backend),
    ]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "frontend_url": frontend,
        "backend_url": backend,
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "next_actions": _next_actions(checks),
    }


def write_artifacts(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "local_dev_smoke.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "local_dev_smoke.md").write_text(_markdown(report), encoding="utf-8")


def _check_frontend_index(fetch: Fetcher, frontend_url: str) -> dict[str, Any]:
    status, body = fetch(f"{frontend_url}/", None)
    has_root = '<div id="root">' in body
    return _check(
        "frontend_index",
        status == 200 and has_root,
        f"status={status}; root={'yes' if has_root else 'no'}",
    )


def _check_frontend_dev_module(fetch: Fetcher, frontend_url: str) -> dict[str, Any]:
    status, body = fetch(f"{frontend_url}/src/main.tsx", None)
    return _check(
        "frontend_dev_module",
        status == 200 and "ReactDOM" in body,
        f"status={status}; vite_module={'yes' if 'ReactDOM' in body else 'no'}",
    )


def _check_backend_health(fetch: Fetcher, backend_url: str) -> dict[str, Any]:
    status, body = fetch(f"{backend_url}/api/v1/health", None)
    healthy = False
    try:
        healthy = json.loads(body).get("status") == "ok"
    except json.JSONDecodeError:
        healthy = False
    return _check("backend_health", status == 200 and healthy, f"status={status}; healthy={healthy}")


def _check_backend_route_data(fetch: Fetcher, backend_url: str) -> dict[str, Any]:
    status, body = fetch(
        f"{backend_url}/api/v1/visits/today?territory_code=WEST-01",
        {"Authorization": f"Bearer {_mock_rep_token()}"},
    )
    count = 0
    try:
        payload = json.loads(body)
        count = len(payload) if isinstance(payload, list) else 0
    except json.JSONDecodeError:
        count = 0
    return _check("backend_route_data", status == 200 and count > 0, f"status={status}; visits={count}")


def _fetch(url: str, headers: dict[str, str] | None) -> FetchResult:
    request = Request(url, headers=headers or {})
    try:
        with urlopen(request, timeout=8) as response:  # noqa: S310 - local operator-provided dev URL.
            return response.status, response.read().decode("utf-8", errors="replace")
    except URLError as exc:
        return 0, str(exc)


def _mock_rep_token() -> str:
    def encode(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    claims = {"sub": "REP-001", "territory_code": "WEST-01", "role": "rep"}
    return f"{encode({'alg': 'none', 'typ': 'JWT'})}.{encode(claims)}."


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail}


def _next_actions(checks: list[dict[str, Any]]) -> list[str]:
    failed = {check["name"] for check in checks if not check["passed"]}
    actions: list[str] = []
    if "backend_health" in failed or "backend_route_data" in failed:
        actions.append("Start backend: cd backend; python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000")
    if "frontend_index" in failed or "frontend_dev_module" in failed:
        actions.append("Start frontend: cd frontend; npm.cmd run dev -- --host 127.0.0.1 --port 5173")
    if not failed:
        actions.append("Open http://localhost:5173/ and hard refresh with Ctrl+Shift+R if Chrome shows a stale blank page.")
    return actions


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Local Dev Smoke",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Frontend: `{report['frontend_url']}`",
        f"- Backend: `{report['backend_url']}`",
        f"- Passed: `{report['passed']}`",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for check in report["checks"]:
        detail = str(check["detail"]).replace("|", "\\|")
        lines.append(f"| {check['name']} | {'pass' if check['passed'] else 'fail'} | {detail} |")
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {action}" for action in report["next_actions"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the local PHANTOM frontend/backend dev loop.")
    parser.add_argument("--frontend-url", default="http://localhost:5173")
    parser.add_argument("--backend-url", default="http://localhost:8000")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/local-dev-smoke"))
    args = parser.parse_args()

    report = build_report(args.frontend_url, args.backend_url)
    write_artifacts(report, args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
