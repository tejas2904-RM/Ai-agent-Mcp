"""Connect to MCP servers and list available tools."""

from __future__ import annotations

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from groww_pulse.config import MCPServerConfig
from groww_pulse.mcp.http_client import discover_http_tools
from groww_pulse.mcp.types import ToolDiscoveryResult


def _resolve_command(command: str) -> str:
    """Use the current interpreter when config says 'python'."""
    if command.lower() in {"python", "python3", "py"}:
        return sys.executable
    return command


async def discover_tools(server: MCPServerConfig) -> ToolDiscoveryResult:
    """Connect to an MCP server and list its tools."""
    if server.transport == "http":
        if not server.url:
            return ToolDiscoveryResult(
                server_name=server.name,
                connected=False,
                error="Missing 'url' for HTTP MCP server.",
            )
        return discover_http_tools(server.url)

    if server.transport != "stdio":
        return ToolDiscoveryResult(
            server_name=server.name,
            connected=False,
            error=f"Unsupported transport '{server.transport}'.",
        )

    if not server.command:
        return ToolDiscoveryResult(
            server_name=server.name,
            connected=False,
            error="Missing 'command' for stdio MCP server.",
        )

    params = StdioServerParameters(
        command=_resolve_command(server.command),
        args=server.args,
        env=server.env or None,
    )

    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                response = await session.list_tools()
                tools = list(response.tools)
                return ToolDiscoveryResult(
                    server_name=server.name,
                    connected=True,
                    tools=tools,
                    tool_names=[tool.name for tool in tools],
                )
    except Exception as exc:  # noqa: BLE001 — surface connection errors in verify output
        return ToolDiscoveryResult(
            server_name=server.name,
            connected=False,
            error=str(exc),
        )


async def discover_all(servers: list[MCPServerConfig]) -> list[ToolDiscoveryResult]:
    results: list[ToolDiscoveryResult] = []
    for server in servers:
        results.append(await discover_tools(server))
    return results


def discover_all_sync(servers: list[MCPServerConfig]) -> list[ToolDiscoveryResult]:
    return asyncio.run(discover_all(servers))
