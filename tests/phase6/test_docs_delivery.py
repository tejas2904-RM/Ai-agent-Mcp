"""Phase 6 Google Docs delivery tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from groww_pulse.phase1.models import NormalizedReview, ReviewSource
from groww_pulse.phase5.models import WeeklyNoteResult, build_note_title, format_week_range
from groww_pulse.phase5.store import WeeklyNoteStore
from groww_pulse.phase6.models import google_doc_url
from groww_pulse.phase6.pipeline import run_docs_delivery
from groww_pulse.phase6.store import DocDeliveryStore
from groww_pulse.mcp.http_client import HttpMCPClient


class MockDocsClient:
    def __init__(self) -> None:
        self.last_title: str | None = None
        self.last_content: str | None = None

    def publish_weekly_note(self, *, title: str, content: str) -> dict[str, Any]:
        self.last_title = title
        self.last_content = content
        document_id = "mock-doc-abc123"
        return {
            "status": "success",
            "document_id": document_id,
            "document_url": google_doc_url(document_id),
            "title": title,
        }


def _save_weekly_note(analysis_dir: Path) -> WeeklyNoteResult:
    week_range = format_week_range(date(2026, 6, 8), date(2026, 6, 26))
    title = build_note_title(week_range)
    content = f"""# {title}

## Top 3 Themes
- Theme one
- Theme two
- Theme three

## User Quotes
- "quote one"
- "quote two"
- "quote three"

## Action Ideas
- Action one
- Action two
- Action three
"""
    result = WeeklyNoteResult(
        model="test",
        week_range=week_range,
        title=title,
        content=content.strip(),
        word_count=40,
        validation_passed=True,
    )
    WeeklyNoteStore(analysis_dir).save(result)
    return result


def test_google_doc_url_format() -> None:
    url = google_doc_url("abc123")
    assert url == "https://docs.google.com/document/d/abc123/edit"


def test_pipeline_persists_doc_delivery(tmp_path: Path) -> None:
    analysis_dir = tmp_path / "analysis"
    _save_weekly_note(analysis_dir)
    mock = MockDocsClient()

    result = run_docs_delivery(analysis_dir=analysis_dir, docs_client=mock)

    assert result.document_id == "mock-doc-abc123"
    assert result.document_url.endswith("/edit")
    assert mock.last_title == result.title
    assert mock.last_content is not None

    reloaded = DocDeliveryStore(analysis_dir).load()
    assert reloaded is not None
    assert reloaded.document_id == result.document_id


def test_http_client_list_tools() -> None:
    client = HttpMCPClient("https://saksham-mcp-server-i1js.onrender.com")
    tools = client.list_tools()
    names = {tool["name"] for tool in tools}
    assert "append_to_doc" in names
