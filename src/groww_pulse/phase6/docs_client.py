"""Google Docs MCP delivery clients (stdio mock + HTTP remote)."""

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
from groww_pulse.phase6.models import google_doc_url


class DocsClientProtocol(Protocol):
    def publish_weekly_note(self, *, title: str, content: str) -> dict[str, Any]: ...


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


class StdioDocsClient:
    """Local mock Google Docs MCP server (docs_create + docs_append)."""

    def __init__(self, server: MCPServerConfig) -> None:
        self.server = server

    async def _publish(self, *, title: str, content: str) -> dict[str, Any]:
        if not self.server.command:
            raise HttpMCPError("Missing stdio command for google-docs MCP server")

        params = StdioServerParameters(
            command=_resolve_command(self.server.command),
            args=self.server.args,
            env=self.server.env or None,
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                create_result = await session.call_tool(
                    "docs_create",
                    arguments={"title": title},
                )
                create_payload = _parse_tool_payload(
                    create_result.content[0] if create_result.content else {}
                )
                document_id = str(
                    create_payload.get("document_id")
                    or create_payload.get("doc_id")
                    or f"mock-{uuid.uuid4().hex[:12]}"
                )
                append_result = await session.call_tool(
                    "docs_append",
                    arguments={"document_id": document_id, "content": content},
                )
                append_payload = _parse_tool_payload(
                    append_result.content[0] if append_result.content else {}
                )
                return {
                    "status": "success",
                    "document_id": document_id,
                    "document_url": google_doc_url(document_id),
                    "title": title,
                    "create_response": create_payload,
                    "append_response": append_payload,
                }

    def publish_weekly_note(self, *, title: str, content: str) -> dict[str, Any]:
        return asyncio.run(self._publish(title=title, content=content))


class HttpDocsClient:
    """Remote Saksham MCP server — append_to_doc only ([tejas2904-RM/MCP](https://github.com/tejas2904-RM/MCP))."""

    def __init__(self, base_url: str, *, doc_id: str) -> None:
        self.client = HttpMCPClient(base_url)
        self.doc_id = doc_id

    def publish_weekly_note(self, *, title: str, content: str) -> dict[str, Any]:
        body = f"# {title}\n\n{content.strip()}\n"
        result = self.client.append_to_doc(doc_id=self.doc_id, content=body)
        document_id = str(result.get("document_id") or self.doc_id)
        return {
            "status": result.get("status", "success"),
            "document_id": document_id,
            "document_url": google_doc_url(document_id),
            "title": title,
            "append_response": result,
        }


def build_docs_client(
    settings: Settings | None = None,
    *,
    server: MCPServerConfig | None = None,
) -> DocsClientProtocol:
    settings = settings or Settings()
    if server is None:
        from groww_pulse.config import load_mcp_servers

        servers = load_mcp_servers(settings.resolve_mcp_config_path())
        docs_servers = [item for item in servers if item.name == "google-docs"]
        if not docs_servers:
            raise HttpMCPError("No google-docs MCP server configured")
        server = docs_servers[0]

    if server.transport == "http":
        if not server.url:
            raise HttpMCPError("HTTP google-docs MCP server missing url")
        if not settings.google_doc_id:
            raise HttpMCPError(
                "GOOGLE_DOC_ID is required for remote Docs MCP (append_to_doc). "
                "Create a Google Doc and set its ID in .env."
            )
        return HttpDocsClient(server.url, doc_id=settings.google_doc_id)

    return StdioDocsClient(server)
