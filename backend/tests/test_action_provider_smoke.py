import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.action_provider_smoke import build_smoke, write_artifacts  # noqa: E402


@pytest.mark.asyncio
async def test_action_provider_smoke_validates_external_payload_contracts() -> None:
    report = await build_smoke()

    assert report["valid"] is True
    assert report["dry_run_only"] is True
    assert report["checks"]["crm_payload_scoped"] is True
    assert report["checks"]["erp_payload_hash_bound"] is True
    assert report["checks"]["erp_approval_id_bound"] is True
    assert {request["path"] for request in report["requests"]} == {"/visit-logs", "/orders"}


@pytest.mark.asyncio
async def test_action_provider_smoke_writes_handoff_artifacts(tmp_path: Path) -> None:
    report = await build_smoke()

    write_artifacts(report, tmp_path)

    assert json.loads((tmp_path / "action_provider_smoke.json").read_text(encoding="utf-8"))["valid"] is True
    markdown = (tmp_path / "action_provider_smoke.md").read_text(encoding="utf-8")
    assert markdown.startswith("# Action Provider Smoke")
    assert "erp_payload_hash_bound" in markdown
