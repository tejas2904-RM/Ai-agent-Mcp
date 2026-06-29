"""Shared MCP client types."""

from __future__ import annotations

from dataclasses import dataclass, field

from mcp.types import Tool


@dataclass
class ToolDiscoveryResult:
    server_name: str
    connected: bool
    tools: list[Tool] = field(default_factory=list)
    tool_names: list[str] = field(default_factory=list)
    error: str | None = None
