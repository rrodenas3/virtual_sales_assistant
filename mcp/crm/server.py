"""CRM local MCP-compatible JSON transport."""

from mcp.crm.tools import preview_visit_log_draft
from mcp.runtime import run_cli

TOOLS = {
    "preview_visit_log_draft": preview_visit_log_draft,
}


def main() -> None:
    run_cli("crm", TOOLS)


if __name__ == "__main__":
    main()
