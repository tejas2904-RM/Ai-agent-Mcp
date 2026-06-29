"""Phase 4 verification — insight selection exit criteria."""

from __future__ import annotations

import sys

from groww_pulse.config import DATA_DIR, Settings
from groww_pulse.phase3.store import AnalysisStore
from groww_pulse.phase4.models import ACTION_IDEA_COUNT, QUOTE_COUNT, TOP_THEME_COUNT
from groww_pulse.phase4.pipeline import InsightSelectionError, run_insight_selection
from groww_pulse.phase4.selection import flatten_allowed_samples, build_insight_packets
from groww_pulse.phase4.store import InsightStore
from groww_pulse.phase4.validators import (
    InsightValidationError,
    find_matching_sample,
    quote_is_pii_free,
    validate_insights,
)


def _print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def run_phase4_verification(*, use_groq: bool = True) -> int:
    settings = Settings()
    analysis_dir = DATA_DIR / "analysis"
    themes_path = analysis_dir / "themes.json"
    insights_path = analysis_dir / "insights.json"
    usage_path = analysis_dir / "groq_usage.json"

    _print_header("Groww Review Pulse - Phase 4 Verification")
    print(f"Input (Phase 3) : {themes_path}")
    print(f"Insights output : {insights_path}")
    print(f"Groq usage log  : {usage_path}")

    theme_store = AnalysisStore(
        themes_path,
        usage_path,
        analysis_dir / "run_metadata.json",
    )
    if theme_store.load_themes() is None:
        print("\nERROR: Phase 3 output not found. Run groww-pulse-phase3 first.")
        return 1

    if use_groq and not settings.groq_api_key:
        print("\nERROR: GROQ_API_KEY is not set. Add it to .env for Phase 4.")
        return 1

    try:
        result, usage = run_insight_selection(use_groq=use_groq, tpm_cooldown=False)
    except (InsightSelectionError, InsightValidationError, FileNotFoundError) as exc:
        print(f"\nERROR: {exc}")
        return 1

    theme_result = theme_store.load_themes()
    assert theme_result is not None
    packets = build_insight_packets(theme_result)
    allowed_samples = flatten_allowed_samples(packets)
    samples_by_id = {sample.id: sample for sample in allowed_samples}

    store = InsightStore(analysis_dir)
    reloaded = store.load_insights()
    reload_ok = reloaded is not None and len(reloaded.quotes) == len(result.quotes)

    validation_ok = True
    try:
        validate_insights(result, allowed_samples)
    except InsightValidationError:
        validation_ok = False

    quotes_traceable = all(
        find_matching_sample(quote.text, quote.review_id, samples_by_id) is not None
        for quote in result.quotes
    )
    quotes_pii_free = all(quote_is_pii_free(quote.text) for quote in result.quotes)
    themes_ok = len(result.top_themes) == TOP_THEME_COUNT
    quotes_ok = len(result.quotes) == QUOTE_COUNT
    actions_ok = len(result.action_ideas) == ACTION_IDEA_COUNT
    actions_linked = all(
        action.theme_name in {theme.name for theme in result.top_themes}
        for action in result.action_ideas
    )

    _print_header("Insight Selection Summary")
    for theme in result.top_themes:
        print(
            f"  #{theme.rank} {theme.name} - severity={theme.severity_score}, "
            f"count={theme.review_count}, sentiment={theme.sentiment_signal}"
        )
    print("\nQuotes:")
    for quote in result.quotes:
        print(f"  [{quote.theme_name}] review #{quote.review_id}: {quote.text[:100]}...")
    print("\nAction ideas:")
    for action in result.action_ideas:
        print(f"  [{action.theme_name}] {action.idea}")

    phase4_usage = [entry for entry in usage.entries if entry.phase == 4]
    if phase4_usage:
        print(f"\nGroq Call #2 tokens: {phase4_usage[-1].total_tokens}")

    _print_header("Phase 4 Exit Criteria")
    checks = [
        (f"Exactly {TOP_THEME_COUNT} top themes selected", themes_ok),
        (f"Exactly {QUOTE_COUNT} PII-free quotes", quotes_ok and quotes_pii_free),
        ("Each quote traceable to a source review sample", quotes_traceable),
        (f"Exactly {ACTION_IDEA_COUNT} theme-linked action ideas", actions_ok and actions_linked),
        ("Insight validation passes", validation_ok),
        ("Artifacts persist and reload correctly", reload_ok),
    ]

    all_passed = True
    for label, ok in checks:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {label}")
        if not ok:
            all_passed = False

    _print_header("Result")
    if all_passed:
        print("Phase 4 complete - ready for Phase 5 (weekly note generation).")
        return 0

    print("Phase 4 incomplete - fix failures above before continuing.")
    return 1


def main() -> None:
    sys.exit(run_phase4_verification())


if __name__ == "__main__":
    main()
