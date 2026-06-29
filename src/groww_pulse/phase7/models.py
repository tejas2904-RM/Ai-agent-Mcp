"""Phase 7 Gmail draft delivery models."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def build_email_body(note_text: str, document_url: str | None = None) -> str:
    """Compose draft body with weekly note and optional Google Doc link."""
    parts = [note_text.strip()]
    if document_url:
        parts.extend(["", "---", f"Full note in Google Docs: {document_url}"])
    return "\n".join(parts)


class DraftDeliveryResult(BaseModel):
    version: int = 1
    subject: str
    recipient: str
    draft_id: str | None = None
    body_chars: int
    includes_doc_link: bool
    document_url: str | None = None
    delivery_method: str
    mcp_server: str
    delivered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
