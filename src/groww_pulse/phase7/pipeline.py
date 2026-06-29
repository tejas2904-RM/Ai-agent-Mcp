"""Phase 7 pipeline — create Gmail draft via MCP."""

from __future__ import annotations

from pathlib import Path

from groww_pulse.config import DATA_DIR, Settings, load_mcp_servers
from groww_pulse.phase5.store import WeeklyNoteStore
from groww_pulse.phase6.store import DocDeliveryStore
from groww_pulse.phase7.gmail_client import GmailClientProtocol, build_gmail_client
from groww_pulse.phase7.models import DraftDeliveryResult, build_email_body
from groww_pulse.phase7.store import DraftDeliveryStore


class GmailDeliveryError(RuntimeError):
    """Raised when Phase 7 Gmail draft delivery fails."""


def run_gmail_delivery(
    analysis_dir: Path | None = None,
    *,
    gmail_client: GmailClientProtocol | None = None,
    recipient: str | None = None,
) -> DraftDeliveryResult:
    settings = Settings()
    analysis_path = analysis_dir or (DATA_DIR / "analysis")

    note_store = WeeklyNoteStore(analysis_path)
    note_result = note_store.load_result()
    note_text = note_store.load_note_text()
    if note_result is None or not note_text:
        raise FileNotFoundError(
            f"Weekly note not found in {analysis_path}. Run Phase 5 first."
        )

    doc_delivery = DocDeliveryStore(analysis_path).load()
    document_url = doc_delivery.document_url if doc_delivery else None
    body = build_email_body(note_text, document_url)

    to_address = (recipient or settings.gmail_recipient or "").strip()
    if not to_address:
        raise GmailDeliveryError(
            "GMAIL_RECIPIENT is not set. Add the draft recipient email to .env."
        )

    client = gmail_client or build_gmail_client(settings)
    gmail_server = next(
        server
        for server in load_mcp_servers(settings.resolve_mcp_config_path())
        if server.name == "gmail"
    )
    delivery_method = (
        "http_create_email_draft"
        if gmail_server.transport == "http"
        else "stdio_gmail_draft_create"
    )
    mcp_server = gmail_server.url or "local-mock-gmail"

    response = client.create_weekly_draft(
        to=to_address,
        subject=note_result.title,
        body=body,
    )
    if response.get("status") not in {None, "success"}:
        raise GmailDeliveryError(
            f"MCP Gmail draft failed: {response.get('message', response)}"
        )

    result = DraftDeliveryResult(
        subject=note_result.title,
        recipient=to_address,
        draft_id=str(response.get("draft_id") or "").strip() or None,
        body_chars=len(body),
        includes_doc_link=bool(document_url),
        document_url=document_url,
        delivery_method=delivery_method,
        mcp_server=mcp_server,
    )
    DraftDeliveryStore(analysis_path).save(result)
    return result
