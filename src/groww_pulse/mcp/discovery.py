"""Validate MCP tool discovery against required tools."""

from __future__ import annotations

from dataclasses import dataclass, field

from groww_pulse.config import MCPServerConfig
from groww_pulse.mcp.types import ToolDiscoveryResult


@dataclass
class RequiredToolCheck:
    logical_name: str
    satisfied: bool
    matched_tool: str | None = None


@dataclass
class ServerValidation:
    server_name: str
    connected: bool
    available_tools: list[str] = field(default_factory=list)
    required_checks: list[RequiredToolCheck] = field(default_factory=list)
    error: str | None = None

    @property
    def all_required_present(self) -> bool:
        return self.connected and all(check.satisfied for check in self.required_checks)


def _resolve_required_tools(server: MCPServerConfig) -> dict[str, list[str]]:
    """Map logical tool names to acceptable aliases on the server."""
    resolved: dict[str, list[str]] = {}
    for tool in server.required_tools:
        aliases = server.tool_aliases.get(tool, [])
        resolved[tool] = [tool, *aliases]
    return resolved


def validate_server(
    server: MCPServerConfig,
    discovery: ToolDiscoveryResult,
) -> ServerValidation:
    if not discovery.connected:
        return ServerValidation(
            server_name=server.name,
            connected=False,
            error=discovery.error,
            required_checks=[
                RequiredToolCheck(logical_name=tool, satisfied=False)
                for tool in server.required_tools
            ],
        )

    available = set(discovery.tool_names)
    checks: list[RequiredToolCheck] = []

    for logical_name, candidates in _resolve_required_tools(server).items():
        matched = next((name for name in candidates if name in available), None)
        checks.append(
            RequiredToolCheck(
                logical_name=logical_name,
                satisfied=matched is not None,
                matched_tool=matched,
            )
        )

    return ServerValidation(
        server_name=server.name,
        connected=True,
        available_tools=sorted(available),
        required_checks=checks,
    )
