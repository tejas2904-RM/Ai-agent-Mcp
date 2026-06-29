"""Phase 7 Gmail draft delivery tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from groww_pulse.phase5.models import WeeklyNoteResult, build_note_title, format_week_range
from groww_pulse.phase5.store import WeeklyNoteStore
from groww_pulse.phase6.models import DocDeliveryResult
from groww_pulse.phase6.store import DocDeliveryStore
from groww_pulse.phase7.models import build_email_body
from groww_pulse.phase7.pipeline import run_gmail_delivery
from groww_pulse.phase7.store import DraftDeliveryStore
from groww_pulse.mcp.http_client import HttpMCPClient


class MockGmailClient:
    def __init__(self) -> None:
        self.last_to: str | None = None
        self.last_subject: str | None = None
        self.last_body: str | None = None

    def create_weekly_draft(
        self, *, to: str, subject: str, body: str
    ) -> dict[str, Any]:
        self.last_to = to
        self.last_subject = subject
        self.last_body = body
        return {
            "status": "success",
            "draft_id": "mock-draft-xyz789",
            "message": "Draft created",
            "to": to,
            "subject": subject,
        }


def _save_weekly_note(analysis_dir: Path) -> WeeklyNoteResult:
    week_range = format_week_range(date(2026, 6, 8), date(2026, 6, 26))
    title = build_note_title(week_range)
    content = """## Top 3 Themes
- Theme one

## User Quotes
- "quote one"

## Action Ideas
- Action one
"""
    result = WeeklyNoteResult(
        model="test",
        week_range=week_range,
        title=title,
        content=content.strip(),
        word_count=20,
        validation_passed=True,
    )
    WeeklyNoteStore(analysis_dir).save(result)
    return result


def test_build_email_body_with_doc_link() -> None:
    body = build_email_body("Weekly pulse text", "https://docs.google.com/document/d/abc/edit")
    assert "Weekly pulse text" in body
    assert "https://docs.google.com/document/d/abc/edit" in body


def test_build_email_body_without_doc_link() -> None:
    body = build_email_body("Weekly pulse text")
    assert body == "Weekly pulse text"
    assert "Google Docs" not in body


def test_pipeline_persists_draft_delivery(tmp_path: Path) -> None:
    analysis_dir = tmp_path / "analysis"
    note = _save_weekly_note(analysis_dir)
    DocDeliveryStore(analysis_dir).save(
        DocDeliveryResult(
            title=note.title,
            document_id="doc-123",
            document_url="https://docs.google.com/document/d/doc-123/edit",
            content_chars=100,
            delivery_method="test",
            mcp_server="test",
        )
    )
    mock = MockGmailClient()

    result = run_gmail_delivery(
        analysis_dir=analysis_dir,
        gmail_client=mock,
        recipient="pulse@example.com",
    )

    assert result.recipient == "pulse@example.com"
    assert result.subject == note.title
    assert result.draft_id == "mock-draft-xyz789"
    assert result.includes_doc_link is True
    assert mock.last_body is not None
    assert "doc-123" in mock.last_body

    reloaded = DraftDeliveryStore(analysis_dir).load()
    assert reloaded is not None
    assert reloaded.recipient == result.recipient


def test_http_client_list_tools_includes_create_email_draft() -> None:
    client = HttpMCPClient("https://saksham-mcp-server-i1js.onrender.com")
    tools = client.list_tools()
    names = {tool["name"] for tool in tools}
    assert "create_email_draft" in names
