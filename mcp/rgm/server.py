"""RGM MCP tool entrypoint placeholder."""

import json

TOOLS = ["get_rgm_recommendations"]


def main() -> None:
    print(json.dumps({"server": "rgm", "transport": "deferred", "tools": TOOLS}))


if __name__ == "__main__":
    main()
