import sys
import json
import subprocess
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.crm.tools import preview_visit_log_draft  # noqa: E402
from mcp.orders.tools import preview_order_draft_payload  # noqa: E402
from mcp.osa.server import TOOLS as OSA_TOOLS  # noqa: E402
from mcp.osa.tools import get_oos_alerts, get_phantom_inventory, get_visit_priority  # noqa: E402
from mcp.rgm.tools import get_rgm_recommendations  # noqa: E402
from mcp.runtime import call_tool, tool_manifest  # noqa: E402
from mcp.shelf_image.server import TOOLS as SHELF_IMAGE_TOOLS  # noqa: E402
from mcp.shelf_image.tools import analyze_shelf_image  # noqa: E402
from mcp.store_master.tools import get_store_health, get_territory_stores  # noqa: E402


@pytest.mark.asyncio
async def test_osa_mcp_tools_return_adapter_backed_data() -> None:
    visits = await get_visit_priority("REP-001", "WEST-01", "2026-06-14")
    assert visits
    assert visits[0]["store_id"]

    alerts = await get_oos_alerts("REP-001", visits[0]["store_id"])
    assert alerts["alerts"]
    assert alerts["page"]["limit"] == 50


@pytest.mark.asyncio
async def test_store_master_and_rgm_mcp_tools_return_json_safe_payloads() -> None:
    store = await get_store_health("ST-001")
    assert store["store_id"] == "ST-001"

    territory = await get_territory_stores("WEST-01", "2026-06-14")
    assert len(territory) == 25

    rgm = await get_rgm_recommendations("ST-001")
    assert rgm["promos"]


@pytest.mark.asyncio
async def test_phantom_inventory_tool_filters_alerts() -> None:
    rows = await get_phantom_inventory("REP-001", "ST-005")
    assert all(row["is_phantom_inventory"] for row in rows)


def test_action_mcp_preview_tools_reuse_service_hashing() -> None:
    draft = preview_order_draft_payload(
        "ST-001",
        "REP-001",
        [{"sku_id": "SKU-4001", "sku_name": "Core SKU 4001", "quantity": 12, "reason": "risk"}],
    )
    assert draft["payload_hash"]
    assert draft["requires_approval"] is True

    visit = preview_visit_log_draft("ST-001", "REP-001", "session-1", "Checked shelf", "completed")
    assert visit["status"] == "DRAFT"
    assert visit["requires_approval"] is False


@pytest.mark.asyncio
async def test_shelf_image_mcp_tool_returns_grounded_findings() -> None:
    alerts = await get_oos_alerts("REP-001", "ST-001")
    result = await analyze_shelf_image(
        "ST-001",
        "REP-001",
        "WEST-01",
        "upload://mcp/image-1",
        [alerts["alerts"][0]["alert_id"]],
    )
    assert result["findings"][0]["grounded_alert_id"] == alerts["alerts"][0]["alert_id"]
    assert result["source_system"] == "mock"


@pytest.mark.asyncio
async def test_mcp_runtime_manifest_and_call_tool() -> None:
    manifest = tool_manifest("osa", OSA_TOOLS)
    assert manifest["transport"] == "local-json"
    assert "get_visit_priority" in manifest["tools"]

    result = await call_tool(
        OSA_TOOLS,
        "get_visit_priority",
        {"rep_id": "REP-001", "territory_code": "WEST-01", "visit_date": "2026-06-14"},
    )
    assert result[0]["store_id"]

    shelf_manifest = tool_manifest("shelf_image", SHELF_IMAGE_TOOLS)
    assert "analyze_shelf_image" in shelf_manifest["tools"]


def test_mcp_server_cli_lists_tools() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "mcp.osa.server", "--list"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    body = json.loads(result.stdout)
    assert body["server"] == "osa"
    assert body["transport"] == "local-json"
