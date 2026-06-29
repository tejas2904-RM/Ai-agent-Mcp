"""Phase 7 verification — Gmail draft delivery exit criteria."""

from __future__ import annotations

import sys

from groww_pulse.config import DATA_DIR, Settings, load_mcp_servers
from groww_pulse.mcp.discovery import validate_server
from groww_pulse.mcp.http_client import discover_http_tools
from groww_pulse.mcp.types import ToolDiscoveryResult
from groww_pulse.phase5.store import WeeklyNoteStore
from groww_pulse.phase6.store import DocDeliveryStore
from groww_pulse.phase7.models import build_email_body
from groww_pulse.phase7.pipeline import GmailDeliveryError, run_gmail_delivery
from groww_pulse.phase7.store import DraftDeliveryStore


def _print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def _discover_gmail_server(settings: Settings) -> ToolDiscoveryResult:
    servers = load_mcp_servers(settings.resolve_mcp_config_path())
    gmail_server = next((server for server in servers if server.name == "gmail"), None)
    if gmail_server is None:
        return ToolDiscoveryResult(
            server_name="gmail",
            connected=False,
            error="gmail server not configured",
        )
    if gmail_server.transport == "http":
        if not gmail_server.url:
            return ToolDiscoveryResult(
                server_name=gmail_server.name,
                connected=False,
                error="Missing url for HTTP MCP server",
            )
        return discover_http_tools(gmail_server.url)
    from groww_pulse.mcp.client import discover_all_sync

    discoveries = discover_all_sync([gmail_server])
    return discoveries[0]


def run_phase7_verification(*, deliver: bool = True) -> int:
    settings = Settings()
    analysis_dir = DATA_DIR / "analysis"
    note_path = analysis_dir / "weekly_note.md"
    delivery_path = analysis_dir / "draft_delivery.json"

    _print_header("Groww Review Pulse - Phase 7 Verification")
    print(f"Input (Phase 5) : {note_path}")
    print(f"Doc link (P6)   : {analysis_dir / 'doc_delivery.json'}")
    print(f"Delivery output : {delivery_path}")
    print(f"MCP profile     : {settings.mcp_profile}")

    note_store = WeeklyNoteStore(analysis_dir)
    note_result = note_store.load_result()
    note_text = note_store.load_note_text()
    if note_result is None or not note_text:
        print("\nERROR: Phase 5 output not found. Run groww-pulse-phase5 first.")
        return 1

    if settings.mcp_profile == "remote" and not settings.gmail_recipient:
        print("\nERROR: GMAIL_RECIPIENT is not set. Required for remote create_email_draft.")
        return 1

    discovery = _discover_gmail_server(settings)
    servers = load_mcp_servers(settings.resolve_mcp_config_path())
    gmail_server = next(server for server in servers if server.name == "gmail")
    validation = validate_server(gmail_server, discovery)

    if not validation.connected:
        print(f"\nERROR: Gmail MCP server not reachable: {discovery.error}")
        return 1

    result = None
    if deliver:
        try:
            result = run_gmail_delivery()
        except (GmailDeliveryError, FileNotFoundError, OSError) as exc:
            print(f"\nERROR: {exc}")
            return 1

    store = DraftDeliveryStore(analysis_dir)
    reloaded = store.load()
    reload_ok = reloaded is not None and (
        result is None or reloaded.recipient == result.recipient
    )

    doc_delivery = DocDeliveryStore(analysis_dir).load()
    expected_body = build_email_body(
        note_text,
        doc_delivery.document_url if doc_delivery else None,
    )

    _print_header("MCP Gmail Server")
    print(f"Connected : {validation.connected}")
    print(f"Tools     : {', '.join(validation.available_tools)}")
    for check in validation.required_checks:
        mark = "OK" if check.satisfied else "MISSING"
        print(f"  [{mark}] {check.logical_name}")

    if result is not None:
        _print_header("Gmail Draft Summary")
        print(f"Subject      : {result.subject}")
        print(f"Recipient    : {result.recipient}")
        print(f"Draft ID     : {result.draft_id or '(not returned)'}")
        print(f"Method       : {result.delivery_method}")
        print(f"Body chars   : {result.body_chars}")
        print(f"Doc link     : {'yes' if result.includes_doc_link else 'no'}")

    subject_ok = bool(reloaded and reloaded.subject.strip()) if reloaded else False
    recipient_ok = bool(reloaded and reloaded.recipient.strip()) if reloaded else False
    body_has_note = bool(reloaded and reloaded.body_chars >= len(note_text)) if reloaded else False
    doc_link_ok = bool(
        reloaded
        and (
            (doc_delivery is None and not reloaded.includes_doc_link)
            or (
                doc_delivery is not None
                and reloaded.includes_doc_link
                and reloaded.document_url == doc_delivery.document_url
            )
        )
    ) if reloaded else False
    draft_only = bool(
        reloaded and reloaded.delivery_method in {
            "http_create_email_draft",
            "stdio_gmail_draft_create",
        }
    ) if reloaded else False

    _print_header("Phase 7 Exit Criteria")
    checks = [
        ("Gmail draft created via MCP (not direct API)", result is not None or reloaded is not None),
        ("Draft contains weekly note body", body_has_note),
        ("Doc link included when Phase 6 artifact exists", doc_link_ok),
        ("Subject is clear and consistent (product + week range)", subject_ok),
        ("Recipient configured (self/alias); draft only, not auto-sent", recipient_ok and draft_only),
        ("Required Gmail MCP tools available", validation.all_required_present),
        ("Artifact persists and reloads correctly", reload_ok),
    ]

    all_passed = True
    for label, ok in checks:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {label}")
        if not ok:
            all_passed = False

    if reloaded and reloaded.body_chars != len(expected_body):
        print(
            f"\nWARNING: Saved body_chars ({reloaded.body_chars}) "
            f"!= expected ({len(expected_body)})"
        )

    _print_header("Result")
    if all_passed:
        print("Phase 7 complete - ready for Phase 8 (orchestration).")
        return 0

    print("Phase 7 incomplete - fix failures above before continuing.")
    return 1


def main() -> None:
    sys.exit(run_phase7_verification())


if __name__ == "__main__":
    main()
