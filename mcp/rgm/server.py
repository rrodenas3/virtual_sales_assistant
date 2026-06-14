"""RGM local MCP-compatible JSON transport."""

from mcp.rgm.tools import get_rgm_recommendations
from mcp.runtime import run_cli

TOOLS = {
    "get_rgm_recommendations": get_rgm_recommendations,
}


def main() -> None:
    run_cli("rgm", TOOLS)


if __name__ == "__main__":
    main()
