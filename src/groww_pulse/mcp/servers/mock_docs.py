"""Local Google Docs MCP server for Phase 0 development and verification."""

from __future__ import annotations

import json
import uuid

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("google-docs")


def _doc_url(document_id: str) -> str:
    return f"https://docs.google.com/document/d/{document_id}/edit"


@mcp.tool()
def docs_create(title: str) -> str:
    """Create a new Google Doc with the given title."""
    document_id = f"mock-{uuid.uuid4().hex[:12]}"
    return json.dumps(
        {
            "status": "success",
            "document_id": document_id,
            "title": title,
            "url": _doc_url(document_id),
        }
    )


@mcp.tool()
def docs_append(document_id: str, content: str) -> str:
    """Append content to an existing Google Doc."""
    return json.dumps(
        {
            "status": "success",
            "document_id": document_id,
            "characters_appended": len(content),
        }
    )


@mcp.tool()
def docs_get(document_id: str) -> str:
    """Read the content of a Google Doc."""
    return json.dumps(
        {
            "status": "success",
            "document_id": document_id,
            "content": f"Document content for {document_id}",
        }
    )


if __name__ == "__main__":
    mcp.run()
