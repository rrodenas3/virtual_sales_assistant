"""OSA local MCP-compatible JSON transport."""

from mcp.osa.tools import get_oos_alerts, get_phantom_inventory, get_visit_priority
from mcp.runtime import run_cli

TOOLS = {
    "get_visit_priority": get_visit_priority,
    "get_oos_alerts": get_oos_alerts,
    "get_phantom_inventory": get_phantom_inventory,
}


def main() -> None:
    run_cli("osa", TOOLS)


if __name__ == "__main__":
    main()
