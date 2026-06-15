"""Manager local MCP-compatible JSON transport."""

from mcp.manager.tools import preview_manager_task_payload, preview_manager_task_status_update
from mcp.runtime import run_cli

TOOLS = {
    "preview_manager_task_payload": preview_manager_task_payload,
    "preview_manager_task_status_update": preview_manager_task_status_update,
}


def main() -> None:
    run_cli("manager", TOOLS)


if __name__ == "__main__":
    main()
