"""Phase 2 verification — PII scrubbing exit criteria."""

from __future__ import annotations

import sys

from groww_pulse.config import DATA_DIR, Settings
from groww_pulse.phase2.pipeline import PiiScrubbingError, scrub_reviews
from groww_pulse.phase2.store import ScrubbedReviewStore
from groww_pulse.phase2.verifier import verify_no_pii


def _print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def run_phase2_verification() -> int:
    settings = Settings()
    scrubbed_path = DATA_DIR / "scrubbed" / "groww_reviews.json"
    report_path = DATA_DIR / "scrubbed" / "pii_scrub_report.json"
    normalized_path = settings.normalized_data_dir / "groww_reviews.json"

    _print_header("Groww Review Pulse — Phase 2 Verification")
    print(f"Input (Phase 1) : {normalized_path}")
    print(f"Output (scrubbed): {scrubbed_path}")
    print(f"Scrub report    : {report_path}")

    if not normalized_path.exists():
        print("\nERROR: Phase 1 output not found. Run groww-pulse-phase1 first.")
        return 1

    try:
        reviews, report = scrub_reviews()
    except PiiScrubbingError as exc:
        print(f"\nERROR: {exc}")
        return 1
    except FileNotFoundError as exc:
        print(f"\nERROR: {exc}")
        return 1

    _print_header("PII Scrubbing Summary")
    print(f"Reviews processed : {report.input_count}")
    print(f"Reviews modified  : {report.reviews_modified}")
    print("PII removed:")
    print(f"  emails    : {report.removed_counts.email}")
    print(f"  phones    : {report.removed_counts.phone}")
    print(f"  usernames : {report.removed_counts.username}")
    print(f"  ids       : {report.removed_counts.id}")
    print(f"  total     : {report.removed_counts.total}")

    store = ScrubbedReviewStore(scrubbed_path, report_path)
    reloaded = store.load_reviews()
    reload_ok = len(reloaded) == report.output_count

    passed, remaining, findings = verify_no_pii(reloaded)
    meaning_ok = all(r.text.strip() for r in reloaded)

    _print_header("Phase 2 Exit Criteria")
    checks = [
        ("Zero emails/phones/usernames/IDs in scrubbed dataset", passed and remaining.total == 0),
        ("Verification log confirms scrubbed categories", report_path.exists()),
        ("No PII in data passed downstream", passed),
        ("Review meaning preserved (non-empty text retained)", meaning_ok),
        ("Scrubbed store persists and reloads correctly", reload_ok),
        ("Mandatory gate passed", report.verification_passed),
    ]

    all_passed = True
    for label, ok in checks:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {label}")
        if not ok:
            all_passed = False

    if findings:
        print("\nRemaining PII samples (up to 3):")
        for finding in findings[:3]:
            print(
                f"  review #{finding.review_index} {finding.field}: "
                f"{finding.category.value} = {finding.value!r}"
            )

    _print_header("Result")
    if all_passed:
        print("Phase 2 complete — ready for Phase 3 (theme analysis).")
        return 0

    print("Phase 2 incomplete — fix failures above before continuing.")
    return 1


def main() -> None:
    sys.exit(run_phase2_verification())


if __name__ == "__main__":
    main()
