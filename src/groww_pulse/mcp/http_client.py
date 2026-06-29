"""HTTP client for the Saksham Google MCP REST server."""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from groww_pulse.mcp.types import ToolDiscoveryResult


class HttpMCPError(RuntimeError):
    """Raised when an HTTP MCP call fails."""


class HttpMCPClientProtocol(Protocol):
    def list_tools(self) -> list[dict[str, str]]: ...

    def append_to_doc(self, *, doc_id: str, content: str) -> dict[str, Any]: ...

    def create_email_draft(
        self, *, to: str, subject: str, body: str
    ) -> dict[str, Any]: ...


class HttpMCPClient:
    """REST client for https://github.com/tejas2904-RM/MCP style servers."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def list_tools(self) -> list[dict[str, str]]:
        response = httpx.get(
            f"{self.base_url}/tools",
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise HttpMCPError(f"Tool discovery failed: HTTP {response.status_code}")
        payload = response.json()
        if not isinstance(payload, list):
            raise HttpMCPError("Tool discovery response must be a list")
        return payload

    def append_to_doc(self, *, doc_id: str, content: str) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/append_to_doc",
            json={"doc_id": doc_id, "content": content},
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise HttpMCPError(
                f"append_to_doc failed: HTTP {response.status_code} — {response.text[:500]}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise HttpMCPError("append_to_doc response must be a JSON object")
        if payload.get("status") == "rejected":
            raise HttpMCPError(payload.get("message", "append_to_doc was rejected"))
        if payload.get("status") == "error":
            raise HttpMCPError(payload.get("message", "append_to_doc returned error"))
        return payload

    def create_email_draft(
        self, *, to: str, subject: str, body: str
    ) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/create_email_draft",
            json={"to": to, "subject": subject, "body": body},
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise HttpMCPError(
                f"create_email_draft failed: HTTP {response.status_code} — {response.text[:500]}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise HttpMCPError("create_email_draft response must be a JSON object")
        if payload.get("status") == "rejected":
            raise HttpMCPError(payload.get("message", "create_email_draft was rejected"))
        if payload.get("status") == "error":
            raise HttpMCPError(payload.get("message", "create_email_draft returned error"))
        return payload


def discover_http_tools(base_url: str) -> ToolDiscoveryResult:
    try:
        client = HttpMCPClient(base_url)
        tools = client.list_tools()
        names = [str(tool.get("name", "")) for tool in tools if tool.get("name")]
        return ToolDiscoveryResult(
            server_name=base_url,
            connected=True,
            tool_names=names,
        )
    except Exception as exc:  # noqa: BLE001
        return ToolDiscoveryResult(
            server_name=base_url,
            connected=False,
            error=str(exc),
        )
