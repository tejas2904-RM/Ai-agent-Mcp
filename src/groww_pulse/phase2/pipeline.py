"""Phase 2 pipeline — load normalized reviews, scrub PII, verify, persist."""

from __future__ import annotations

from pathlib import Path

from groww_pulse.config import Settings
from groww_pulse.phase1.models import NormalizedReview
from groww_pulse.phase1.store import ReviewStore
from groww_pulse.phase2.models import CategoryCounts, ScrubReport
from groww_pulse.phase2.scrubber import scrub_review
from groww_pulse.phase2.store import ScrubbedReviewStore
from groww_pulse.phase2.verifier import verify_no_pii


class PiiScrubbingError(RuntimeError):
    """Raised when PII remains after scrubbing (mandatory gate failure)."""


def scrub_reviews(
    input_path: Path | None = None,
    output_path: Path | None = None,
    report_path: Path | None = None,
    *,
    fail_on_remaining_pii: bool = True,
) -> tuple[list[NormalizedReview], ScrubReport]:
    settings = Settings()
    normalized_path = input_path or (settings.normalized_data_dir / "groww_reviews.json")
    scrubbed_path = output_path or (settings.scrubbed_data_dir / "groww_reviews.json")
    scrub_report_path = report_path or (settings.scrubbed_data_dir / "pii_scrub_report.json")

    if not normalized_path.exists():
        raise FileNotFoundError(
            f"Normalized reviews not found at {normalized_path}. Run Phase 1 first."
        )

    source_reviews = ReviewStore(normalized_path).load()
    removed_totals = CategoryCounts()
    scrubbed_reviews: list[NormalizedReview] = []
    modified_count = 0

    for review in source_reviews:
        scrubbed, counts, modified = scrub_review(review)
        scrubbed_reviews.append(scrubbed)
        removed_totals.add(counts)
        if modified:
            modified_count += 1

    passed, remaining, findings = verify_no_pii(scrubbed_reviews)

    report = ScrubReport(
        input_path=str(normalized_path),
        output_path=str(scrubbed_path),
        report_path=str(scrub_report_path),
        input_count=len(source_reviews),
        output_count=len(scrubbed_reviews),
        reviews_modified=modified_count,
        removed_counts=removed_totals,
        verification_passed=passed,
        verification_remaining=remaining,
    )

    store = ScrubbedReviewStore(scrubbed_path, scrub_report_path)
    store.save(scrubbed_reviews, report)

    if fail_on_remaining_pii and not passed:
        sample = findings[:3]
        details = ", ".join(f"{f.category.value} in {f.field}" for f in sample)
        raise PiiScrubbingError(
            f"PII detected after scrubbing ({len(findings)} finding(s): {details}). "
            "Mandatory gate failed."
        )

    return scrubbed_reviews, report
