"""Orders local MCP-compatible JSON transport."""

from mcp.orders.tools import preview_order_draft_payload
from mcp.runtime import run_cli

TOOLS = {
    "preview_order_draft_payload": preview_order_draft_payload,
}


def main() -> None:
    run_cli("orders", TOOLS)


if __name__ == "__main__":
    main()
