from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import sys
from collections.abc import Awaitable, Callable
from typing import Any

ToolFunc = Callable[..., Any] | Callable[..., Awaitable[Any]]


def _json_default(value: Any) -> str:
    return str(value)


async def call_tool(tools: dict[str, ToolFunc], name: str, arguments: dict[str, Any]) -> Any:
    tool = tools.get(name)
    if tool is None:
        raise KeyError(f"Unknown tool: {name}")
    result = tool(**arguments)
    if inspect.isawaitable(result):
        return await result
    return result


def tool_manifest(server_name: str, tools: dict[str, ToolFunc]) -> dict[str, Any]:
    return {
        "server": server_name,
        "transport": "local-json",
        "tools": sorted(tools),
    }


async def run_stdio(server_name: str, tools: dict[str, ToolFunc]) -> None:
    print(json.dumps(tool_manifest(server_name, tools), sort_keys=True), flush=True)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            result = await call_tool(tools, request["tool"], request.get("arguments", {}))
            response = {"ok": True, "result": result}
        except Exception as exc:  # noqa: BLE001
            response = {"ok": False, "error": str(exc)}
        print(json.dumps(response, default=_json_default, sort_keys=True), flush=True)


def run_cli(server_name: str, tools: dict[str, ToolFunc]) -> None:
    parser = argparse.ArgumentParser(description=f"{server_name} local MCP-compatible JSON transport")
    parser.add_argument("--list", action="store_true", help="Print tool manifest and exit")
    parser.add_argument("--call", help="Invoke one tool by name")
    parser.add_argument("--args-json", default="{}", help="JSON object passed as tool arguments")
    args = parser.parse_args()

    if args.list:
        print(json.dumps(tool_manifest(server_name, tools), sort_keys=True))
        return
    if args.call:
        arguments = json.loads(args.args_json)
        result = asyncio.run(call_tool(tools, args.call, arguments))
        print(json.dumps({"ok": True, "result": result}, default=_json_default, sort_keys=True))
        return
    asyncio.run(run_stdio(server_name, tools))
