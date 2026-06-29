"""Post-scrub PII verification."""

from __future__ import annotations

import re

from groww_pulse.phase1.models import NormalizedReview
from groww_pulse.phase2.models import CategoryCounts, PiiCategory, PiiMatch
from groww_pulse.phase2.scrubber import (
    EMAIL_PATTERN,
    ID_PATTERNS,
    PHONE_PATTERN,
    USERNAME_PATTERN,
)


def _find_matches(
    text: str,
    field: str,
    category: PiiCategory,
    pattern: re.Pattern[str],
    review_index: int,
) -> list[PiiMatch]:
    return [
        PiiMatch(
            category=category,
            value=match.group(0),
            field=field,
            review_index=review_index,
        )
        for match in pattern.finditer(text)
    ]


def scan_text(text: str, field: str, review_index: int) -> list[PiiMatch]:
    findings: list[PiiMatch] = []
    findings.extend(
        _find_matches(text, field, PiiCategory.EMAIL, EMAIL_PATTERN, review_index)
    )
    findings.extend(
        _find_matches(text, field, PiiCategory.PHONE, PHONE_PATTERN, review_index)
    )
    findings.extend(
        _find_matches(text, field, PiiCategory.USERNAME, USERNAME_PATTERN, review_index)
    )
    for pattern in ID_PATTERNS:
        findings.extend(
            _find_matches(text, field, PiiCategory.ID, pattern, review_index)
        )
    return findings


def scan_reviews(reviews: list[NormalizedReview]) -> list[PiiMatch]:
    findings: list[PiiMatch] = []
    for index, review in enumerate(reviews):
        findings.extend(scan_text(review.title, "title", index))
        findings.extend(scan_text(review.text, "text", index))
    return findings


def verify_no_pii(reviews: list[NormalizedReview]) -> tuple[bool, CategoryCounts, list[PiiMatch]]:
    findings = scan_reviews(reviews)
    remaining = CategoryCounts()
    for finding in findings:
        remaining.increment(finding.category)
    return len(findings) == 0, remaining, findings
