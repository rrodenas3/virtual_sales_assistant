"""Store Master MCP tool entrypoint placeholder."""

import json

TOOLS = ["get_store_health", "get_territory_stores"]


def main() -> None:
    print(json.dumps({"server": "store_master", "transport": "deferred", "tools": TOOLS}))


if __name__ == "__main__":
    main()
