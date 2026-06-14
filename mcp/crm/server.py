"""CRM MCP tool entrypoint placeholder."""

import json

TOOLS = ["preview_visit_log_draft"]


def main() -> None:
    print(json.dumps({"server": "crm", "transport": "deferred", "tools": TOOLS}))


if __name__ == "__main__":
    main()
