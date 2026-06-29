"""Phase 5 weekly note generation tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from groww_pulse.phase1.models import NormalizedReview, ReviewSource
from groww_pulse.phase1.store import ReviewStore
from groww_pulse.phase2.pipeline import scrub_reviews
from groww_pulse.phase3.models import GroqUsageEntry
from groww_pulse.phase3.pipeline import run_theme_analysis
from groww_pulse.phase4.pipeline import run_insight_selection
from groww_pulse.phase5.models import MAX_WORD_COUNT
from groww_pulse.phase5.pipeline import run_weekly_note_generation
from groww_pulse.phase5.store import WeeklyNoteStore
from groww_pulse.phase5.validators import count_words, validate_note


def _review(
    text: str,
    *,
    rating: int = 3,
    title: str = "Feedback",
    review_date: date = date(2026, 6, 20),
) -> NormalizedReview:
    return NormalizedReview(
        source=ReviewSource.PLAY_STORE,
        rating=rating,
        title=title,
        text=text,
        date=review_date,
    )


class MockThemeGroqClient:
    def chat_completion(self, **kwargs: Any) -> tuple[dict[str, Any], GroqUsageEntry]:
        _ = kwargs
        return {
            "themes": [
                {
                    "name": "Payments & withdrawals",
                    "summary": "Withdrawal and UPI pain.",
                    "volume_signal": "medium",
                    "sentiment_signal": "negative",
                    "merged_from": ["payments_withdrawals"],
                },
                {
                    "name": "Trading & orders",
                    "summary": "Order execution issues.",
                    "volume_signal": "high",
                    "sentiment_signal": "mixed",
                    "merged_from": ["trading_orders"],
                },
                {
                    "name": "App UX & support",
                    "summary": "Crashes and login failures.",
                    "volume_signal": "medium",
                    "sentiment_signal": "mixed",
                    "merged_from": ["app_ux_support"],
                },
                {
                    "name": "Mutual funds & SIP",
                    "summary": "SIP feedback.",
                    "volume_signal": "low",
                    "sentiment_signal": "positive",
                    "merged_from": ["mutual_funds_sip"],
                },
                {
                    "name": "Onboarding & KYC",
                    "summary": "KYC delays.",
                    "volume_signal": "low",
                    "sentiment_signal": "negative",
                    "merged_from": ["onboarding_kyc"],
                },
            ]
        }, GroqUsageEntry(
            call_id="phase3_theme_analysis",
            phase=3,
            purpose="theme_analysis",
            model="test",
            estimated_input_tokens=1000,
            total_tokens=1100,
            max_tokens=800,
        )

    def chat_completion_text(self, **kwargs: Any) -> tuple[str, GroqUsageEntry]:
        _ = kwargs
        note = """# Groww Weekly Review Pulse - Jun 20 - Jun 20, 2026

## Top 3 Themes
- **Payments & withdrawals** — Withdrawal delays dominate complaints (medium volume, negative sentiment).
- **Trading & orders** — Order execution reliability needs attention (high volume, mixed sentiment).
- **App UX & support** — Crashes and login issues persist (medium volume, mixed sentiment).

## User Quotes
- "Withdrawal still pending to my bank account for five days"
- "Order execution failed again during market open"
- "App crashes after latest update and login fails"

## Action Ideas
- **Payments & withdrawals:** Audit withdrawal SLA and show live transfer status in-app.
- **Trading & orders:** Improve order routing during market open volatility.
- **App UX & support:** Prioritize crash fixes in the latest release train.
"""
        return note.strip(), GroqUsageEntry(
            call_id=kwargs.get("call_id", "phase5_note_generation"),
            phase=5,
            purpose=kwargs.get("purpose", "note_generation"),
            model="test",
            estimated_input_tokens=600,
            total_tokens=900,
            max_tokens=400,
        )


def _prepare_analysis(tmp_path: Path, reviews: list[NormalizedReview]) -> Path:
    input_path = tmp_path / "normalized.json"
    scrubbed_path = tmp_path / "scrubbed.json"
    report_path = tmp_path / "report.json"
    analysis_dir = tmp_path / "analysis"
    ReviewStore(input_path).save(reviews)
    scrub_reviews(
        input_path=input_path,
        output_path=scrubbed_path,
        report_path=report_path,
    )
    run_theme_analysis(
        input_path=scrubbed_path,
        output_dir=analysis_dir,
        groq_client=MockThemeGroqClient(),
    )
    run_insight_selection(
        analysis_dir=analysis_dir,
        use_groq=False,
        tpm_cooldown=False,
    )
    return analysis_dir


def test_validate_note_counts_words_and_sections() -> None:
    note = """# Groww Weekly Review Pulse - Jun 01 - Jun 07, 2026

## Top 3 Themes
- Theme one summary here
- Theme two summary here
- Theme three summary here

## User Quotes
- "quote one"
- "quote two"
- "quote three"

## Action Ideas
- Action one
- Action two
- Action three
"""
    result = validate_note(note)
    assert result.passed
    assert result.word_count <= MAX_WORD_COUNT
    assert result.theme_items >= 3
    assert result.quote_items >= 3
    assert result.action_items >= 3


def test_count_words_basic() -> None:
    assert count_words("one two three") == 3


def test_pipeline_generates_note_with_mock_groq(tmp_path: Path) -> None:
    quote_text = "Withdrawal still pending to my bank account for five days"
    reviews = [
        _review(quote_text, rating=1),
        _review("Order execution failed again during market open", rating=2),
        _review("App crashes after latest update and login fails", rating=2),
        _review("SIP in mutual fund works smoothly", rating=5),
        _review("KYC verification is stuck for weeks", rating=2),
        _review("Excellent overall investing experience on Groww", rating=5),
    ]
    analysis_dir = _prepare_analysis(tmp_path, reviews)

    result, usage = run_weekly_note_generation(
        analysis_dir=analysis_dir,
        groq_client=MockThemeGroqClient(),
        allow_retry=False,
    )

    assert result.validation_passed
    assert result.word_count <= MAX_WORD_COUNT
    assert any(entry.phase == 5 for entry in usage.entries)

    store = WeeklyNoteStore(analysis_dir)
    assert store.load_note_text() == result.content
    assert validate_note(result.content).passed


def test_fallback_note_without_groq(tmp_path: Path) -> None:
    reviews = [
        _review("withdrawal issue with bank transfer", rating=1),
        _review("order failed during trading", rating=2),
        _review("app crash on login", rating=2),
        _review("sip investment good", rating=5),
        _review("kyc pending", rating=2),
        _review("nice app", rating=5),
    ]
    analysis_dir = _prepare_analysis(tmp_path, reviews)

    result, _ = run_weekly_note_generation(
        analysis_dir=analysis_dir,
        use_groq=False,
    )

    assert result.validation_passed
    assert "## Top 3 Themes" in result.content
    assert validate_note(result.content).passed
