"""Phase 2 PII scrubbing tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from groww_pulse.phase1.models import NormalizedReview, ReviewSource
from groww_pulse.phase1.store import ReviewStore
from groww_pulse.phase2.pipeline import scrub_reviews
from groww_pulse.phase2.scrubber import scrub_review, scrub_text
from groww_pulse.phase2.verifier import verify_no_pii


def _review(text: str, title: str = "Support issue") -> NormalizedReview:
    return NormalizedReview(
        source=ReviewSource.PLAY_STORE,
        rating=3,
        title=title,
        text=text,
        date=date(2026, 6, 1),
    )


def test_scrub_email_phone_username_id() -> None:
    raw = (
        "Contact me at john.doe@example.com or +91-9876543210. "
        "My PAN is ABCDE1234F and username: trader_john. Order id #ORD99887766."
    )
    result = scrub_text(raw)
    assert "[REDACTED_EMAIL]" in result.text
    assert "[REDACTED_PHONE]" in result.text
    assert "[REDACTED_USERNAME]" in result.text
    assert "[REDACTED_ID]" in result.text
    assert "john.doe@example.com" not in result.text
    assert "9876543210" not in result.text


def test_verify_clean_text_passes() -> None:
    reviews = [
        _review("The app is slow during market open but otherwise works well for SIP.")
    ]
    passed, remaining, findings = verify_no_pii(reviews)
    assert passed
    assert remaining.total == 0
    assert not findings


def test_pipeline_scrubs_and_persists(tmp_path: Path) -> None:
    input_path = tmp_path / "normalized.json"
    output_path = tmp_path / "scrubbed.json"
    report_path = tmp_path / "report.json"

    reviews = [
        _review("Reach support at help@groww.test or call 9876543210 please fix KYC."),
        _review("Great mutual fund experience with clear dashboard and charts."),
    ]
    ReviewStore(input_path).save(reviews)

    scrubbed, report = scrub_reviews(
        input_path=input_path,
        output_path=output_path,
        report_path=report_path,
    )

    assert len(scrubbed) == 2
    assert report.reviews_modified == 1
    assert report.verification_passed
    assert output_path.exists()
    assert report_path.exists()
    assert "help@groww.test" not in scrubbed[0].text


def test_meaning_preserved_after_scrub() -> None:
    review, counts, modified = scrub_review(
        _review("Email me at a@b.co about the broken withdrawal flow this week.")
    )
    assert modified
    assert counts.email == 1
    assert "withdrawal flow" in review.text
    assert len(review.text.split()) > 3
