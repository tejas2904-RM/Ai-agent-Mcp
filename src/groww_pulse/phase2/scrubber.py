"""Detect and mask PII in review text."""

from __future__ import annotations

import re
from dataclasses import dataclass

from groww_pulse.phase1.models import NormalizedReview
from groww_pulse.phase2.models import CategoryCounts, PiiCategory

MASK = {
    PiiCategory.EMAIL: "[REDACTED_EMAIL]",
    PiiCategory.PHONE: "[REDACTED_PHONE]",
    PiiCategory.USERNAME: "[REDACTED_USERNAME]",
    PiiCategory.ID: "[REDACTED_ID]",
}

# --- Detection patterns (also used by verifier) ---

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)

# Indian mobile (+91 optional) and explicit international +prefix numbers
PHONE_PATTERN = re.compile(
    r"""
    (?:
        (?:(?:\+|00)?91[\s-]?)?[6-9]\d{9}
        |
        \+\d{1,3}[\s-]?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# @handles and explicit username mentions
USERNAME_PATTERN = re.compile(
    r"""
    (?:
        @[A-Za-z0-9_.]{2,30}
        |
        (?:(?:username|user\s*name|handle)\s*[:=]\s*[A-Za-z0-9_.-]{2,30})
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
AADHAAR_PATTERN = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
UUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
# Account / order / reference IDs (keyword-led or long numeric tokens)
ID_KEYWORD_PATTERN = re.compile(
    r"""
    (?:
        (?:account|acct|customer|client|order|txn|transaction|ref|reference|id|user\s*id)
        \s*[#:=]?\s*
        [A-Za-z0-9-]{4,20}
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
LONG_NUMERIC_ID_PATTERN = re.compile(r"\b\d{10,16}\b")

ID_PATTERNS: list[re.Pattern[str]] = [
    PAN_PATTERN,
    AADHAAR_PATTERN,
    UUID_PATTERN,
    ID_KEYWORD_PATTERN,
    LONG_NUMERIC_ID_PATTERN,
]

PATTERN_MAP: list[tuple[PiiCategory, re.Pattern[str]]] = [
    (PiiCategory.EMAIL, EMAIL_PATTERN),
    (PiiCategory.PHONE, PHONE_PATTERN),
    (PiiCategory.USERNAME, USERNAME_PATTERN),
]


@dataclass
class ScrubFieldResult:
    text: str
    counts: CategoryCounts
    modified: bool


def _apply_pattern(text: str, category: PiiCategory, pattern: re.Pattern[str]) -> tuple[str, int]:
    matches = pattern.findall(text)
    if not matches:
        return text, 0
    return pattern.sub(MASK[category], text), len(matches)


def _apply_id_patterns(text: str) -> tuple[str, int]:
    total = 0
    result = text
    for pattern in ID_PATTERNS:
        matches = pattern.findall(result)
        if matches:
            result = pattern.sub(MASK[PiiCategory.ID], result)
            total += len(matches)
    return result, total


def scrub_text(text: str) -> ScrubFieldResult:
    """Remove/mask PII in a single text field."""
    counts = CategoryCounts()
    result = text
    modified = False

    for category, pattern in PATTERN_MAP:
        result, n = _apply_pattern(result, category, pattern)
        if n:
            counts.increment(category, n)
            modified = True

    result, id_count = _apply_id_patterns(result)
    if id_count:
        counts.increment(PiiCategory.ID, id_count)
        modified = True

    result = re.sub(r"\s+", " ", result).strip()
    return ScrubFieldResult(text=result, counts=counts, modified=modified)


def scrub_review(review: NormalizedReview) -> tuple[NormalizedReview, CategoryCounts, bool]:
    """Scrub title and text; return updated review and per-review counts."""
    title_result = scrub_text(review.title)
    text_result = scrub_text(review.text)

    combined = CategoryCounts()
    combined.add(title_result.counts)
    combined.add(text_result.counts)

    modified = title_result.modified or text_result.modified
    scrubbed = review.model_copy(
        update={
            "title": title_result.text or "(No title)",
            "text": text_result.text,
        }
    )
    return scrubbed, combined, modified
