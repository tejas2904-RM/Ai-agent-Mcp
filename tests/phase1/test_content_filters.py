"""Tests for Phase 1 content filters."""

from __future__ import annotations

from datetime import date

from groww_pulse.phase1.content_filters import (
    clean_review_text,
    is_english,
    remove_emojis,
    review_word_count,
)
from groww_pulse.phase1.filters import normalize_row
from groww_pulse.phase1.models import ReviewSource


def test_remove_emojis() -> None:
    assert remove_emojis("Great app! 🚀 Love it ❤️") == "Great app! Love it"
    title, text = clean_review_text("Nice 👍", "Works well for SIP investing daily")
    assert "👍" not in title
    assert "👍" not in text


def test_word_count_more_than_six_required() -> None:
    assert review_word_count("(No title)", "Too short review here") == 4
    assert (
        review_word_count(
            "Good app",
            "This is a solid app for mutual fund and stock investing",
        )
        >= 7
    )


def test_english_only() -> None:
    assert is_english("The app is very easy to use for beginners")
    assert not is_english("बहुत अच्छा ऐप है निवेश के लिए")


def test_normalize_row_rejects_short_and_non_english() -> None:
    window_start = date(2026, 1, 1)
    window_end = date(2026, 12, 31)

    _, skip_short, _ = normalize_row(
        {
            "rating": "5",
            "title": "Ok",
            "text": "Too short text here",
            "date": "2026-06-01",
        },
        ReviewSource.PLAY_STORE,
        1,
        window_start,
        window_end,
    )
    assert skip_short is not None
    assert "Too few words" in skip_short.reason

    _, skip_hindi, _ = normalize_row(
        {
            "rating": "5",
            "title": "Review",
            "text": "यह ऐप बहुत अच्छा है और निवेश करना आसान बनाता है",
            "date": "2026-06-01",
        },
        ReviewSource.PLAY_STORE,
        2,
        window_start,
        window_end,
    )
    assert skip_hindi is not None
    assert skip_hindi.reason == "Non-English review"

    review, skip_ok, _ = normalize_row(
        {
            "rating": "4",
            "title": "Smooth SIP",
            "text": "Monthly SIP setup was seamless and the dashboard is clear",
            "date": "2026-06-01",
        },
        ReviewSource.PLAY_STORE,
        3,
        window_start,
        window_end,
    )
    assert skip_ok is None
    assert review is not None
    assert "🚀" not in review.text
