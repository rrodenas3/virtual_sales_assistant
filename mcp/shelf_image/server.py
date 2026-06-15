"""Shelf image local MCP-compatible JSON transport."""

from mcp.runtime import run_cli
from mcp.shelf_image.tools import analyze_shelf_image

TOOLS = {
    "analyze_shelf_image": analyze_shelf_image,
}


def main() -> None:
    run_cli("shelf_image", TOOLS)


if __name__ == "__main__":
    main()
