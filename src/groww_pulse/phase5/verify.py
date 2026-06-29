"""Phase 5 verification — weekly note generation exit criteria."""

from __future__ import annotations

import sys

from groww_pulse.config import DATA_DIR, Settings
from groww_pulse.phase4.store import InsightStore
from groww_pulse.phase5.models import MAX_WORD_COUNT
from groww_pulse.phase5.pipeline import WeeklyNoteError, run_weekly_note_generation
from groww_pulse.phase5.store import WeeklyNoteStore
from groww_pulse.phase5.validators import NoteValidationError, note_is_pii_free, validate_note


def _print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def run_phase5_verification(*, use_groq: bool = True) -> int:
    settings = Settings()
    analysis_dir = DATA_DIR / "analysis"
    insights_path = analysis_dir / "insights.json"
    note_path = analysis_dir / "weekly_note.md"
    usage_path = analysis_dir / "groq_usage.json"

    _print_header("Groww Review Pulse - Phase 5 Verification")
    print(f"Input (Phase 4) : {insights_path}")
    print(f"Note output     : {note_path}")
    print(f"Groq usage log  : {usage_path}")

    if InsightStore(analysis_dir).load_insights() is None:
        print("\nERROR: Phase 4 output not found. Run groww-pulse-phase4 first.")
        return 1

    if use_groq and not settings.groq_api_key:
        print("\nERROR: GROQ_API_KEY is not set. Add it to .env for Phase 5.")
        return 1

    try:
        result, usage = run_weekly_note_generation(use_groq=use_groq, allow_retry=True)
    except (WeeklyNoteError, NoteValidationError, FileNotFoundError) as exc:
        print(f"\nERROR: {exc}")
        return 1

    store = WeeklyNoteStore(analysis_dir)
    reloaded_text = store.load_note_text()
    reload_ok = reloaded_text == result.content

    validation = validate_note(result.content)
    phase5_usage = [entry for entry in usage.entries if entry.phase == 5]

    _print_header("Weekly Note Summary")
    print(f"Title       : {result.title}")
    print(f"Week range  : {result.week_range}")
    print(f"Word count  : {result.word_count} (max {MAX_WORD_COUNT})")
    print(f"Groq calls  : {result.groq_calls}")
    if phase5_usage:
        print(f"Call tokens : {sum(entry.total_tokens for entry in phase5_usage)}")
    print("\nPreview:")
    preview_lines = result.content.splitlines()[:12]
    for line in preview_lines:
        print(f"  {line}")
    if len(result.content.splitlines()) > 12:
        print("  ...")

    _print_header("Phase 5 Exit Criteria")
    checks = [
        (f"Word count <= {MAX_WORD_COUNT}", validation.word_count_ok),
        ("Top 3 themes section with 3 items", validation.theme_items >= 3),
        ("User quotes section with 3 items", validation.quote_items >= 3),
        ("Action ideas section with 3 items", validation.action_items >= 3),
        ("No PII in final note", validation.pii_ok),
        ("Scannable markdown layout", validation.scannable_ok),
        ("Note persists and reloads correctly", reload_ok),
    ]

    all_passed = True
    for label, ok in checks:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {label}")
        if not ok:
            all_passed = False

    _print_header("Result")
    if all_passed:
        print("Phase 5 complete - ready for Phase 6 (Google Docs delivery).")
        return 0

    print("Phase 5 incomplete - fix failures above before continuing.")
    return 1


def main() -> None:
    sys.exit(run_phase5_verification())


if __name__ == "__main__":
    main()
