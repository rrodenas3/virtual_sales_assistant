"""Store Master local MCP-compatible JSON transport."""

from mcp.runtime import run_cli
from mcp.store_master.tools import get_store_health, get_territory_stores

TOOLS = {
    "get_store_health": get_store_health,
    "get_territory_stores": get_territory_stores,
}


def main() -> None:
    run_cli("store_master", TOOLS)


if __name__ == "__main__":
    main()
