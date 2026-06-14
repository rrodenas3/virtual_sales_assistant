"""OSA MCP tool entrypoint placeholder.

Transport wiring is intentionally deferred. The importable functions in
`mcp.osa.tools` are the source of truth for local MCP behavior.
"""

import json

TOOLS = ["get_visit_priority", "get_oos_alerts", "get_phantom_inventory"]


def main() -> None:
    print(json.dumps({"server": "osa", "transport": "deferred", "tools": TOOLS}))


if __name__ == "__main__":
    main()
