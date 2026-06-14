import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.crm.tools import preview_visit_log_draft  # noqa: E402
from mcp.orders.tools import preview_order_draft_payload  # noqa: E402
from mcp.osa.tools import get_oos_alerts, get_phantom_inventory, get_visit_priority  # noqa: E402
from mcp.rgm.tools import get_rgm_recommendations  # noqa: E402
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
