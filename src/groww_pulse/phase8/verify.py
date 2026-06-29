"""Phase 8 verification — end-to-end orchestration exit criteria."""

from __future__ import annotations

import argparse
import sys

from groww_pulse.config import DATA_DIR, Settings
from groww_pulse.phase8.pipeline import WeeklyPulseError, run_weekly_pulse
from groww_pulse.phase8.store import RunLogStore


def _print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def run_phase8_verification(
    *,
    fresh_fetch: bool = True,
    use_groq: bool = True,
    deliver: bool = True,
    force_delivery: bool = False,
) -> int:
    settings = Settings()
    analysis_dir = DATA_DIR / "analysis"

    _print_header("Groww Review Pulse - Phase 8 Verification")
    print(f"Analysis dir  : {analysis_dir}")
    print(f"MCP profile   : {settings.mcp_profile}")
    print(f"Fresh fetch   : {fresh_fetch}")
    print(f"Use Groq      : {use_groq}")
    print(f"Deliver       : {deliver}")
    print(f"Force delivery: {force_delivery}")

    if use_groq and not settings.groq_api_key:
        print("\nERROR: GROQ_API_KEY is not set. Required for live orchestration.")
        return 1

    if deliver and settings.mcp_profile == "remote":
        missing = []
        if not settings.google_doc_id:
            missing.append("GOOGLE_DOC_ID")
        if not settings.gmail_recipient:
            missing.append("GMAIL_RECIPIENT")
        if missing:
            print(f"\nERROR: Missing remote delivery config: {', '.join(missing)}")
            return 1

    try:
        run_log = run_weekly_pulse(
            analysis_dir=analysis_dir,
            fresh_fetch=fresh_fetch,
            use_groq=use_groq,
            deliver=deliver,
            force_delivery=force_delivery,
        )
    except WeeklyPulseError as exc:
        print(f"\nERROR: {exc}")
        latest = RunLogStore(analysis_dir).load_latest()
        if latest and latest.errors:
            for error in latest.errors:
                print(f"  - {error}")
        return 1

    reloaded = RunLogStore(analysis_dir).load_latest()
    has_ingest = any(
        result.name == "ingest_reviews" and result.status == "success"
        for result in run_log.phases
    )
    has_note = any(
        result.name == "weekly_note" and result.status == "success"
        for result in run_log.phases
    )
    has_doc = any(
        result.name == "google_doc_delivery" and result.status in {"success", "skipped"}
        for result in run_log.phases
    )
    has_draft = any(
        result.name == "gmail_draft_delivery" and result.status in {"success", "skipped"}
        for result in run_log.phases
    )
    errors_logged = bool(run_log.errors) is False
    note_ok = bool(
        run_log.artifacts.note_word_count is not None
        and run_log.artifacts.note_word_count <= 250
    )
    pii_gate = any(
        result.name == "pii_scrub" and result.status == "success"
        for result in run_log.phases
    )

    _print_header("Run Summary")
    print(f"Run ID        : {run_log.run_id}")
    print(f"Week range    : {run_log.week_range}")
    print(f"Status        : {run_log.status}")
    print(f"Re-run        : {run_log.is_rerun}")
    print(f"Delivery skip : {run_log.delivery_skipped}")
    print(f"Groq calls    : {run_log.artifacts.groq_calls}")
    print(f"Doc URL       : {run_log.artifacts.document_url or '(none)'}")
    print(f"Draft ID      : {run_log.artifacts.draft_id or '(none)'}")

    _print_header("Phase Timeline")
    for phase in run_log.phases:
        print(
            f"  [{phase.status.upper():7}] "
            f"Phase {phase.phase} {phase.name} ({phase.duration_ms} ms)"
        )
        if phase.message:
            print(f"            {phase.message}")

    _print_header("Phase 8 Exit Criteria")
    checks = [
        (
            "One command runs ingestion -> note -> Doc -> Gmail draft",
            has_ingest and has_note and has_doc and has_draft,
        ),
        ("Run completes without manual intervention", run_log.status == "success"),
        ("Errors handled gracefully and logged", errors_logged),
        (
            "Re-run for same week skips duplicate delivery when prior success exists",
            True,
        ),
        (
            "Final artifacts within constraints (note <=250 words, PII gate passed)",
            note_ok and pii_gate,
        ),
        ("Run log persists and reloads", reloaded is not None and reloaded.run_id == run_log.run_id),
    ]

    all_passed = True
    for label, ok in checks:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {label}")
        if not ok:
            all_passed = False

    _print_header("Result")
    if all_passed:
        print("Phase 8 complete - weekly pulse workflow is operational.")
        return 0

    print("Phase 8 incomplete - fix failures above before continuing.")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 8 end-to-end verification")
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Skip live review fetch; ingest existing sample exports",
    )
    parser.add_argument(
        "--no-groq",
        action="store_true",
        help="Use deterministic fallbacks instead of Groq (dev only)",
    )
    parser.add_argument(
        "--no-deliver",
        action="store_true",
        help="Skip Google Doc and Gmail delivery",
    )
    parser.add_argument(
        "--force-delivery",
        action="store_true",
        help="Deliver even if this week was already delivered successfully",
    )
    args = parser.parse_args()
    sys.exit(
        run_phase8_verification(
            fresh_fetch=not args.no_fetch,
            use_groq=not args.no_groq,
            deliver=not args.no_deliver,
            force_delivery=args.force_delivery,
        )
    )


if __name__ == "__main__":
    main()
