"""Gmail MCP draft clients (stdio mock + HTTP remote)."""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from typing import Any, Protocol

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from groww_pulse.config import MCPServerConfig, Settings
from groww_pulse.mcp.http_client import HttpMCPClient, HttpMCPError


class GmailClientProtocol(Protocol):
    def create_weekly_draft(
        self, *, to: str, subject: str, body: str
    ) -> dict[str, Any]: ...


def _resolve_command(command: str) -> str:
    if command.lower() in {"python", "python3", "py"}:
        return sys.executable
    return command


def _parse_tool_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"status": "success", "message": raw}
    if hasattr(raw, "text"):
        return _parse_tool_payload(raw.text)
    return {"status": "success", "message": str(raw)}


class StdioGmailClient:
    """Local mock Gmail MCP server (gmail_draft_create)."""

    def __init__(self, server: MCPServerConfig) -> None:
        self.server = server

    async def _create_draft(
        self, *, to: str, subject: str, body: str
    ) -> dict[str, Any]:
        if not self.server.command:
            raise HttpMCPError("Missing stdio command for gmail MCP server")

        params = StdioServerParameters(
            command=_resolve_command(self.server.command),
            args=self.server.args,
            env=self.server.env or None,
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "gmail_draft_create",
                    arguments={"to": to, "subject": subject, "body": body},
                )
                payload = _parse_tool_payload(
                    result.content[0] if result.content else {}
                )
                draft_id = str(
                    payload.get("draft_id") or f"mock-draft-{uuid.uuid4().hex[:12]}"
                )
                return {
                    "status": payload.get("status", "success"),
                    "draft_id": draft_id,
                    "message": payload.get("message", "Draft created"),
                    "to": to,
                    "subject": subject,
                }

    def create_weekly_draft(
        self, *, to: str, subject: str, body: str
    ) -> dict[str, Any]:
        return asyncio.run(self._create_draft(to=to, subject=subject, body=body))


class HttpGmailClient:
    """Remote Saksham MCP server — create_email_draft."""

    def __init__(self, base_url: str) -> None:
        self.client = HttpMCPClient(base_url)

    def create_weekly_draft(
        self, *, to: str, subject: str, body: str
    ) -> dict[str, Any]:
        result = self.client.create_email_draft(to=to, subject=subject, body=body)
        return {
            "status": result.get("status", "success"),
            "draft_id": result.get("draft_id"),
            "message": result.get("message", "Draft created"),
            "to": to,
            "subject": subject,
            "raw_response": result,
        }


def build_gmail_client(
    settings: Settings | None = None,
    *,
    server: MCPServerConfig | None = None,
) -> GmailClientProtocol:
    settings = settings or Settings()
    if server is None:
        from groww_pulse.config import load_mcp_servers

        servers = load_mcp_servers(settings.resolve_mcp_config_path())
        gmail_servers = [item for item in servers if item.name == "gmail"]
        if not gmail_servers:
            raise HttpMCPError("No gmail MCP server configured")
        server = gmail_servers[0]

    if server.transport == "http":
        if not server.url:
            raise HttpMCPError("HTTP gmail MCP server missing url")
        if not settings.gmail_recipient:
            raise HttpMCPError(
                "GMAIL_RECIPIENT is required for remote Gmail MCP (create_email_draft). "
                "Set the draft recipient email in .env."
            )
        return HttpGmailClient(server.url)

    return StdioGmailClient(server)
