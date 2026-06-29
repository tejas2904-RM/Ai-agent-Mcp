"""Phase 6 Google Docs delivery models."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def google_doc_url(document_id: str) -> str:
    return f"https://docs.google.com/document/d/{document_id}/edit"


class DocDeliveryResult(BaseModel):
    version: int = 1
    title: str
    document_id: str
    document_url: str
    content_chars: int
    delivery_method: str
    mcp_server: str
    delivered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
