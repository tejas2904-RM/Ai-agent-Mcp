"""Phase 6 pipeline — publish weekly note to Google Docs via MCP."""

from __future__ import annotations

from pathlib import Path

from groww_pulse.config import DATA_DIR, Settings, load_mcp_servers
from groww_pulse.phase5.store import WeeklyNoteStore
from groww_pulse.phase6.docs_client import DocsClientProtocol, build_docs_client
from groww_pulse.phase6.models import DocDeliveryResult, google_doc_url
from groww_pulse.phase6.store import DocDeliveryStore


class DocsDeliveryError(RuntimeError):
    """Raised when Phase 6 Google Docs delivery fails."""


def run_docs_delivery(
    analysis_dir: Path | None = None,
    *,
    docs_client: DocsClientProtocol | None = None,
) -> DocDeliveryResult:
    settings = Settings()
    analysis_path = analysis_dir or (DATA_DIR / "analysis")

    note_store = WeeklyNoteStore(analysis_path)
    note_result = note_store.load_result()
    note_text = note_store.load_note_text()
    if note_result is None or not note_text:
        raise FileNotFoundError(
            f"Weekly note not found in {analysis_path}. Run Phase 5 first."
        )

    client = docs_client or build_docs_client(settings)
    docs_server = next(
        server
        for server in load_mcp_servers(settings.resolve_mcp_config_path())
        if server.name == "google-docs"
    )
    delivery_method = (
        "http_append_to_doc"
        if docs_server.transport == "http"
        else "stdio_docs_create_append"
    )
    mcp_server = docs_server.url or "local-mock-google-docs"

    response = client.publish_weekly_note(
        title=note_result.title,
        content=note_text,
    )
    document_id = str(response.get("document_id", "")).strip()
    if not document_id:
        raise DocsDeliveryError("MCP Docs tool did not return a document_id")

    document_url = str(response.get("document_url") or google_doc_url(document_id))
    if response.get("status") not in {None, "success"}:
        raise DocsDeliveryError(
            f"MCP Docs delivery failed: {response.get('message', response)}"
        )

    result = DocDeliveryResult(
        title=note_result.title,
        document_id=document_id,
        document_url=document_url,
        content_chars=len(note_text),
        delivery_method=delivery_method,
        mcp_server=mcp_server,
    )
    DocDeliveryStore(analysis_path).save(result)
    return result
