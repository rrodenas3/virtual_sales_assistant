from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.local_dev_smoke import build_report, write_artifacts  # noqa: E402


def test_local_dev_smoke_passes_with_expected_dev_services() -> None:
    def fake_fetch(url: str, headers: dict[str, str] | None) -> tuple[int, str]:
        if url == "http://frontend/":
            return 200, '<html><body><div id="root"></div></body></html>'
        if url == "http://frontend/src/main.tsx":
            return 200, "ReactDOM.createRoot(document.getElementById('root')!)"
        if url == "http://backend/api/v1/health":
            return 200, '{"status":"ok"}'
        if url == "http://backend/api/v1/visits/today?territory_code=WEST-01":
            assert headers is not None
            assert headers["Authorization"].startswith("Bearer ")
            return 200, '[{"store_id":"ST-001"}]'
        return 404, ""

    report = build_report("http://frontend", "http://backend", fetcher=fake_fetch)

    assert report["passed"] is True
    assert {check["name"] for check in report["checks"]} == {
        "frontend_index",
        "frontend_dev_module",
        "backend_health",
        "backend_route_data",
    }
    assert report["next_actions"] == [
        "Open http://localhost:5173/ and hard refresh with Ctrl+Shift+R if Chrome shows a stale blank page."
    ]


def test_local_dev_smoke_failure_names_start_commands() -> None:
    def fake_fetch(_url: str, _headers: dict[str, str] | None) -> tuple[int, str]:
        return 0, "connection refused"

    report = build_report("http://frontend", "http://backend", fetcher=fake_fetch)

    assert report["passed"] is False
    assert any("Start backend:" in action for action in report["next_actions"])
    assert any("Start frontend:" in action for action in report["next_actions"])


def test_local_dev_smoke_writes_json_and_markdown(tmp_path: Path) -> None:
    report = {
        "generated_at": "2026-06-16T00:00:00+00:00",
        "frontend_url": "http://frontend",
        "backend_url": "http://backend",
        "passed": True,
        "checks": [{"name": "frontend_index", "passed": True, "detail": "status=200"}],
        "next_actions": ["Open http://localhost:5173/."],
    }

    write_artifacts(report, tmp_path)

    assert json.loads((tmp_path / "local_dev_smoke.json").read_text(encoding="utf-8"))["passed"] is True
    assert "# Local Dev Smoke" in (tmp_path / "local_dev_smoke.md").read_text(encoding="utf-8")
