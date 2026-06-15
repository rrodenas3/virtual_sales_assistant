import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.memory_provider_smoke import build_smoke, write_artifacts  # noqa: E402


@pytest.mark.asyncio
async def test_memory_provider_smoke_validates_scoped_mem0_contract() -> None:
    report = await build_smoke()

    assert report["valid"] is True
    assert report["checks"]["disabled_default_has_no_memory"] is True
    assert report["checks"]["search_scoped_to_rep_store"] is True
    assert report["checks"]["write_scoped_to_session_store"] is True
    assert report["memory_count"] == 1


@pytest.mark.asyncio
async def test_memory_provider_smoke_writes_handoff_artifacts(tmp_path: Path) -> None:
    report = await build_smoke()

    write_artifacts(report, tmp_path)

    assert json.loads((tmp_path / "memory_provider_smoke.json").read_text(encoding="utf-8"))["valid"] is True
    markdown = (tmp_path / "memory_provider_smoke.md").read_text(encoding="utf-8")
    assert markdown.startswith("# Memory Provider Smoke")
    assert "search_scoped_to_rep_store" in markdown
