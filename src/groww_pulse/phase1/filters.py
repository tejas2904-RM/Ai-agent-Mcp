"""Date, rating, deduplication, and recency window filters."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from groww_pulse.phase1.content_filters import (
    MIN_REVIEW_WORDS,
    clean_review_text,
    is_english,
    review_word_count,
)
from groww_pulse.phase1.models import NormalizedReview, ReviewSource, SkippedRow

DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
    "%b %d, %Y",
    "%B %d, %Y",
)


def parse_rating(raw: str) -> int | None:
    cleaned = raw.strip().lower()
    if not cleaned:
        return None

    match = re.search(r"(\d)", cleaned)
    if not match:
        return None

    value = int(match.group(1))
    if 1 <= value <= 5:
        return value
    return None


def parse_date(raw: str, reference: date | None = None) -> date | None:
    text = raw.strip()
    if not text:
        return None

    # ISO date prefix (handles timestamps with timezone suffix)
    iso_prefix = text[:10]
    for candidate in (text, iso_prefix):
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue

    # Fallback: fromisoformat for extended ISO strings
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    return None


def recency_window(
    weeks: int,
    reference: date | None = None,
) -> tuple[date, date]:
    """Return inclusive [start, end] dates for the last N weeks."""
    end = reference or date.today()
    start = end - timedelta(weeks=weeks)
    return start, end


def within_window(review_date: date, start: date, end: date) -> bool:
    return start <= review_date <= end


def dedupe_key(review: NormalizedReview) -> tuple[str, int, str, str, str]:
    return (
        review.source.value,
        review.rating,
        review.title.strip().lower(),
        review.text.strip().lower(),
        review.date.isoformat(),
    )


def remove_duplicates(
    reviews: list[NormalizedReview],
) -> tuple[list[NormalizedReview], int]:
    seen: set[tuple[str, int, str, str, str]] = set()
    unique: list[NormalizedReview] = []
    removed = 0

    for review in reviews:
        key = dedupe_key(review)
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        unique.append(review)

    return unique, removed


def normalize_row(
    raw: dict[str, str],
    source: ReviewSource,
    row_number: int,
    window_start: date,
    window_end: date,
) -> tuple[NormalizedReview | None, SkippedRow | None, bool]:
    """
    Normalize one raw row.

    Returns (review, skipped, outside_window).
    outside_window is True when the row parsed but fell outside the recency window.
    """
    rating = parse_rating(raw["rating"])
    if rating is None:
        return None, SkippedRow(
            source=source,
            row_number=row_number,
            reason=f"Invalid rating: {raw['rating']!r}",
            raw_preview=raw["text"][:80],
        ), False

    review_date = parse_date(raw["date"])
    if review_date is None:
        return None, SkippedRow(
            source=source,
            row_number=row_number,
            reason=f"Unparseable date: {raw['date']!r}",
            raw_preview=raw["text"][:80],
        ), False

    if not within_window(review_date, window_start, window_end):
        return None, None, True

    title, text = clean_review_text(raw["title"], raw["text"])

    if not text:
        return None, SkippedRow(
            source=source,
            row_number=row_number,
            reason="Empty review text after cleaning",
            raw_preview=raw["text"][:80],
        ), False

    words = review_word_count(title, text)
    if words < MIN_REVIEW_WORDS:
        return None, SkippedRow(
            source=source,
            row_number=row_number,
            reason=f"Too few words ({words}; need more than 6)",
            raw_preview=text[:80],
        ), False

    if not is_english(text):
        return None, SkippedRow(
            source=source,
            row_number=row_number,
            reason="Non-English review",
            raw_preview=text[:80],
        ), False

    review = NormalizedReview(
        source=source,
        rating=rating,
        title=title or "(No title)",
        text=text,
        date=review_date,
    )
    return review, None, False
