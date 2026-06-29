"""Local Gmail MCP server for Phase 0 development and verification."""

import json
import uuid

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("gmail")


@mcp.tool()
def gmail_draft_create(to: str, subject: str, body: str) -> str:
    """Create a Gmail draft email (does not send)."""
    return json.dumps(
        {
            "status": "success",
            "message": "Draft created",
            "draft_id": f"mock-draft-{uuid.uuid4().hex[:12]}",
            "to": to,
            "subject": subject,
            "body_chars": len(body),
        }
    )


@mcp.tool()
def gmail_list_drafts(max_results: int = 10) -> str:
    """List recent Gmail drafts."""
    return f"Listing up to {max_results} drafts"


if __name__ == "__main__":
    mcp.run()
