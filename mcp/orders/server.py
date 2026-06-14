"""Orders MCP tool entrypoint placeholder."""

import json

TOOLS = ["preview_order_draft_payload"]


def main() -> None:
    print(json.dumps({"server": "orders", "transport": "deferred", "tools": TOOLS}))


if __name__ == "__main__":
    main()
