"""Phase 3 verification — theme analysis exit criteria."""

from __future__ import annotations

import sys

from groww_pulse.config import DATA_DIR, Settings
from groww_pulse.phase3.models import MAX_THEMES, REVIEW_CAP
from groww_pulse.phase3.pipeline import ThemeAnalysisError, run_theme_analysis
from groww_pulse.phase3.store import AnalysisStore


def _print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def _dominant_theme_share(result) -> float:
    if not result.themes:
        return 0.0
    total = sum(theme.review_count for theme in result.themes)
    if total == 0:
        return 0.0
    return max(theme.review_count for theme in result.themes) / total


def _assignment_coverage(metadata) -> bool:
    assigned_ids = {item.review_id for item in metadata.assignments}
    expected = set(range(metadata.reviews_analyzed))
    return assigned_ids == expected


def run_phase3_verification(*, use_groq: bool = True) -> int:
    settings = Settings()
    scrubbed_path = settings.scrubbed_data_dir / "groww_reviews.json"
    analysis_dir = DATA_DIR / "analysis"
    themes_path = analysis_dir / "themes.json"
    usage_path = analysis_dir / "groq_usage.json"
    metadata_path = analysis_dir / "run_metadata.json"

    _print_header("Groww Review Pulse - Phase 3 Verification")
    print(f"Input (Phase 2) : {scrubbed_path}")
    print(f"Themes output   : {themes_path}")
    print(f"Groq usage log  : {usage_path}")
    print(f"Run metadata    : {metadata_path}")

    if not scrubbed_path.exists():
        print("\nERROR: Phase 2 output not found. Run groww-pulse-phase2 first.")
        return 1

    if use_groq and not settings.groq_api_key:
        print("\nERROR: GROQ_API_KEY is not set. Add it to .env for Phase 3.")
        return 1

    try:
        result, usage, metadata = run_theme_analysis(use_groq=use_groq)
    except (ThemeAnalysisError, FileNotFoundError, ValueError) as exc:
        print(f"\nERROR: {exc}")
        return 1

    store = AnalysisStore(themes_path, usage_path, metadata_path)
    reloaded = store.load_themes()
    reload_ok = reloaded is not None and len(reloaded.themes) == len(result.themes)

    theme_count_ok = 0 < len(result.themes) <= MAX_THEMES
    signals_ok = all(
        theme.volume_signal and theme.sentiment_signal for theme in result.themes
    )
    assignment_ok = _assignment_coverage(metadata)
    dominant_share = _dominant_theme_share(result)
    dominant_ok = dominant_share < 0.85
    cap_ok = metadata.reviews_analyzed <= REVIEW_CAP
    token_budget_ok = metadata.estimated_call1_input_tokens <= 3_500

    _print_header("Pre-LLM Summary")
    print(f"Scrubbed total     : {metadata.scrubbed_total}")
    print(f"Reviews analyzed   : {metadata.reviews_analyzed} (cap {REVIEW_CAP})")
    print(f"Reviews dropped    : {metadata.reviews_dropped}")
    print(f"Samples / bucket   : {metadata.samples_per_bucket}")
    print(f"Call #1 est. input : {metadata.estimated_call1_input_tokens} tokens")
    print("Bucket counts:")
    for key, count in sorted(metadata.bucket_counts.items()):
        print(f"  {key}: {count}")

    _print_header("Theme Analysis Summary")
    for index, theme in enumerate(result.themes, start=1):
        print(
            f"  {index}. {theme.name} - count={theme.review_count}, "
            f"avg={theme.avg_rating}, low_star={theme.low_star_pct}%, "
            f"severity={theme.severity_score}, "
            f"volume={theme.volume_signal}, sentiment={theme.sentiment_signal}"
        )
    if use_groq:
        print(f"\nGroq total tokens : {usage.total_tokens}")

    _print_header("Phase 3 Exit Criteria")
    checks = [
        (f"<= {MAX_THEMES} themes produced", theme_count_ok),
        ("Every analyzed review assigned to a seed bucket", assignment_ok),
        ("Each theme has volume/sentiment indicator", signals_ok),
        ("No single theme trivially absorbs everything (<85%)", dominant_ok),
        (f"Review cap applied ({REVIEW_CAP})", cap_ok),
        ("Call #1 input token estimate within budget", token_budget_ok),
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
        print("Phase 3 complete - ready for Phase 4 (insight selection).")
        return 0

    print("Phase 3 incomplete - fix failures above before continuing.")
    return 1


def main() -> None:
    sys.exit(run_phase3_verification())


if __name__ == "__main__":
    main()
