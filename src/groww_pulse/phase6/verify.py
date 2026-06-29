"""Phase 6 verification — Google Docs delivery exit criteria."""

from __future__ import annotations

import sys

from groww_pulse.config import DATA_DIR, Settings, load_mcp_servers
from groww_pulse.mcp.client import discover_all_sync
from groww_pulse.mcp.types import ToolDiscoveryResult
from groww_pulse.mcp.discovery import validate_server
from groww_pulse.mcp.http_client import discover_http_tools
from groww_pulse.phase5.store import WeeklyNoteStore
from groww_pulse.phase6.docs_client import build_docs_client
from groww_pulse.phase6.models import google_doc_url
from groww_pulse.phase6.pipeline import DocsDeliveryError, run_docs_delivery
from groww_pulse.phase6.store import DocDeliveryStore


def _print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def _discover_docs_server(settings: Settings) -> ToolDiscoveryResult:
    servers = load_mcp_servers(settings.resolve_mcp_config_path())
    docs_server = next((server for server in servers if server.name == "google-docs"), None)
    if docs_server is None:
        return ToolDiscoveryResult(
            server_name="google-docs",
            connected=False,
            error="google-docs server not configured",
        )
    if docs_server.transport == "http":
        if not docs_server.url:
            return ToolDiscoveryResult(
                server_name=docs_server.name,
                connected=False,
                error="Missing url for HTTP MCP server",
            )
        return discover_http_tools(docs_server.url)
    discoveries = discover_all_sync([docs_server])
    return discoveries[0]


def run_phase6_verification(*, deliver: bool = True) -> int:
    settings = Settings()
    analysis_dir = DATA_DIR / "analysis"
    note_path = analysis_dir / "weekly_note.md"
    delivery_path = analysis_dir / "doc_delivery.json"

    _print_header("Groww Review Pulse - Phase 6 Verification")
    print(f"Input (Phase 5) : {note_path}")
    print(f"Delivery output : {delivery_path}")
    print(f"MCP profile     : {settings.mcp_profile}")

    note_store = WeeklyNoteStore(analysis_dir)
    if note_store.load_note_text() is None:
        print("\nERROR: Phase 5 output not found. Run groww-pulse-phase5 first.")
        return 1

    if settings.mcp_profile == "remote" and not settings.google_doc_id:
        print("\nERROR: GOOGLE_DOC_ID is not set. Required for remote append_to_doc.")
        return 1

    discovery = _discover_docs_server(settings)
    servers = load_mcp_servers(settings.resolve_mcp_config_path())
    docs_server = next(server for server in servers if server.name == "google-docs")
    validation = validate_server(docs_server, discovery)

    if not validation.connected:
        print(f"\nERROR: Google Docs MCP server not reachable: {discovery.error}")
        return 1

    result = None
    if deliver:
        try:
            result = run_docs_delivery()
        except (DocsDeliveryError, FileNotFoundError, OSError) as exc:
            print(f"\nERROR: {exc}")
            return 1

    store = DocDeliveryStore(analysis_dir)
    reloaded = store.load()
    reload_ok = reloaded is not None and (
        result is None or reloaded.document_id == result.document_id
    )

    _print_header("MCP Docs Server")
    print(f"Connected : {validation.connected}")
    print(f"Tools     : {', '.join(validation.available_tools)}")
    for check in validation.required_checks:
        mark = "OK" if check.satisfied else "MISSING"
        print(f"  [{mark}] {check.logical_name}")

    if result is not None:
        _print_header("Doc Delivery Summary")
        print(f"Title        : {result.title}")
        print(f"Document ID  : {result.document_id}")
        print(f"Document URL : {result.document_url}")
        print(f"Method       : {result.delivery_method}")
        print(f"Content chars: {result.content_chars}")

    title_ok = bool(reloaded and reloaded.title.strip()) if reloaded else False
    url_ok = bool(
        reloaded
        and reloaded.document_url.startswith("https://docs.google.com/document/d/")
    )
    id_ok = bool(reloaded and reloaded.document_id)
    link_matches = bool(
        reloaded and reloaded.document_url == google_doc_url(reloaded.document_id)
    )

    _print_header("Phase 6 Exit Criteria")
    checks = [
        ("Google Doc published via MCP (not direct Google API)", result is not None or reloaded is not None),
        ("Doc delivery metadata saved with document link", id_ok and url_ok),
        ("Doc has clear, consistent title (product + week range)", title_ok),
        ("Document URL matches document ID", link_matches),
        ("Required Docs MCP tools available", validation.all_required_present),
        ("Artifact persists and reloads correctly", reload_ok),
    ]

    all_passed = True
    for label, ok in checks:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {label}")
        if not ok:
            all_passed = False

    _print_header("Result")
    if all_passed:
        print("Phase 6 complete - ready for Phase 7 (Gmail draft delivery).")
        return 0

    print("Phase 6 incomplete - fix failures above before continuing.")
    return 1


def main() -> None:
    sys.exit(run_phase6_verification())


if __name__ == "__main__":
    main()
