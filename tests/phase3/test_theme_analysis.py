"""Phase 3 theme analysis tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from groww_pulse.phase1.models import NormalizedReview, ReviewSource
from groww_pulse.phase1.store import ReviewStore
from groww_pulse.phase2.pipeline import scrub_reviews
from groww_pulse.phase3.aggregation import (
    assign_buckets,
    build_theme_packets,
    cap_reviews,
    compute_dataset_stats,
)
from groww_pulse.phase3.buckets import GENERAL_THEME_KEY, match_theme_key
from groww_pulse.phase3.groq_client import GroqTokenBudgetError, validate_pre_call_budget
from groww_pulse.phase3.models import GroqUsageEntry, MAX_THEMES
from groww_pulse.phase3.pipeline import run_theme_analysis
from groww_pulse.phase3.store import AnalysisStore
from groww_pulse.phase3.theme_agent import normalize_llm_themes


def _review(
    text: str,
    *,
    rating: int = 3,
    title: str = "Feedback",
    review_date: date = date(2026, 6, 20),
    source: ReviewSource = ReviewSource.PLAY_STORE,
) -> NormalizedReview:
    return NormalizedReview(
        source=source,
        rating=rating,
        title=title,
        text=text,
        date=review_date,
    )


class MockGroqClient:
    def chat_completion(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int,
        call_id: str,
        phase: int,
        purpose: str,
        estimated_input_tokens: int,
        response_format: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], GroqUsageEntry]:
        _ = messages, max_tokens, response_format
        payload = {
            "themes": [
                {
                    "name": "Payments & withdrawals",
                    "summary": "Withdrawals and UPI issues dominate complaints.",
                    "volume_signal": "medium",
                    "sentiment_signal": "negative",
                    "merged_from": ["payments_withdrawals"],
                    "review_count": 40,
                    "avg_rating": 2.4,
                    "low_star_pct": 62.0,
                },
                {
                    "name": "Trading & orders",
                    "summary": "Order execution and trading reliability concerns.",
                    "volume_signal": "high",
                    "sentiment_signal": "mixed",
                    "merged_from": ["trading_orders", "general_experience"],
                    "review_count": 120,
                    "avg_rating": 3.1,
                    "low_star_pct": 44.0,
                },
                {
                    "name": "App UX & support",
                    "summary": "Crashes, login, and support responsiveness.",
                    "volume_signal": "medium",
                    "sentiment_signal": "mixed",
                    "merged_from": ["app_ux_support"],
                    "review_count": 35,
                    "avg_rating": 3.3,
                    "low_star_pct": 37.0,
                },
            ]
        }
        usage = GroqUsageEntry(
            call_id=call_id,
            phase=phase,
            purpose=purpose,
            model="llama-3.3-70b-versatile",
            estimated_input_tokens=estimated_input_tokens,
            prompt_tokens=estimated_input_tokens,
            completion_tokens=250,
            total_tokens=estimated_input_tokens + 250,
            max_tokens=max_tokens,
        )
        return payload, usage


def test_cap_reviews_keeps_most_recent() -> None:
    reviews = [
        _review("older", review_date=date(2026, 4, 1)),
        _review("newer", review_date=date(2026, 6, 1)),
    ]
    capped, dropped = cap_reviews(reviews, max_reviews=1)
    assert dropped == 1
    assert len(capped) == 1
    assert capped[0].review.text == "newer"


def test_bucket_assignment_covers_every_review() -> None:
    reviews = [
        _review("My order failed during intraday trading", rating=2),
        _review("Withdrawal to bank is delayed again", rating=1),
        _review("Great app experience overall", rating=5),
    ]
    indexed, _ = cap_reviews(reviews, max_reviews=10)
    buckets, assignments = assign_buckets(indexed)
    assert len(assignments) == 3
    assert match_theme_key(reviews[0]) == "trading_orders"
    assert match_theme_key(reviews[1]) == "payments_withdrawals"
    assert match_theme_key(reviews[2]) == GENERAL_THEME_KEY
    assert GENERAL_THEME_KEY in buckets


def test_build_packets_respect_sample_limit() -> None:
    reviews = [
        _review(f"order issue number {index}", rating=1 + (index % 5))
        for index in range(12)
    ]
    indexed, _ = cap_reviews(reviews, max_reviews=12)
    buckets, _ = assign_buckets(indexed)
    packets = build_theme_packets(buckets, samples_per_bucket=8)
    packet = next(packet for packet in packets if packet.theme_key == "trading_orders")
    assert packet.review_count == 12
    assert len(packet.samples) <= 8


def test_validate_pre_call_budget_rejects_large_input() -> None:
    try:
        validate_pre_call_budget(
            4_000,
            800,
            max_input_tokens=3_500,
            max_total_tokens=6_000,
        )
        raised = False
    except GroqTokenBudgetError:
        raised = True
    assert raised


def test_normalize_llm_themes_caps_at_five() -> None:
    reviews = [
        _review("order failed", rating=2),
        _review("withdrawal delayed", rating=1),
        _review("kyc pending", rating=2),
        _review("sip investment", rating=5),
        _review("app crash on login", rating=2),
        _review("nice overall", rating=5),
    ]
    indexed, _ = cap_reviews(reviews, max_reviews=10)
    buckets, _ = assign_buckets(indexed)
    packets = build_theme_packets(buckets, samples_per_bucket=2)
    stats = compute_dataset_stats(indexed)
    payload = {
        "themes": [
            {
                "name": f"Theme {index}",
                "summary": "summary",
                "volume_signal": "low",
                "sentiment_signal": "mixed",
                "merged_from": [packet.theme_key],
            }
            for index, packet in enumerate(packets)
        ]
    }
    themes = normalize_llm_themes(payload, packets, stats)
    assert len(themes) <= MAX_THEMES
    assert all(theme.severity_score >= 0 for theme in themes)


def test_pipeline_persists_outputs_with_mock_groq(tmp_path: Path) -> None:
    input_path = tmp_path / "normalized.json"
    scrubbed_path = tmp_path / "scrubbed.json"
    report_path = tmp_path / "report.json"
    output_dir = tmp_path / "analysis"

    reviews = [
        _review("Order execution failed again during market open", rating=2),
        _review("Withdrawal still pending to my bank account", rating=1),
        _review("KYC verification is stuck for weeks", rating=2),
        _review("SIP in mutual fund works smoothly", rating=5),
        _review("App crashes after latest update and login fails", rating=2),
        _review("Excellent overall investing experience on Groww", rating=5),
    ]
    ReviewStore(input_path).save(reviews)
    scrub_reviews(
        input_path=input_path,
        output_path=scrubbed_path,
        report_path=report_path,
    )

    result, usage, metadata = run_theme_analysis(
        input_path=scrubbed_path,
        output_dir=output_dir,
        groq_client=MockGroqClient(),
    )

    assert len(result.themes) <= MAX_THEMES
    assert metadata.reviews_analyzed == len(reviews)
    assert metadata.estimated_call1_input_tokens <= 3_500
    assert usage.total_tokens > 0

    store = AnalysisStore(
        output_dir / "themes.json",
        output_dir / "groq_usage.json",
        output_dir / "run_metadata.json",
    )
    assert store.load_themes() is not None
    assert store.load_metadata() is not None


def test_pipeline_without_groq_uses_fallback(tmp_path: Path) -> None:
    input_path = tmp_path / "normalized.json"
    scrubbed_path = tmp_path / "scrubbed.json"
    report_path = tmp_path / "report.json"
    output_dir = tmp_path / "analysis"

    reviews = [
        _review("order failed", rating=2),
        _review("withdrawal issue", rating=1),
        _review("great app", rating=5),
    ]
    ReviewStore(input_path).save(reviews)
    scrub_reviews(
        input_path=input_path,
        output_path=scrubbed_path,
        report_path=report_path,
    )

    result, usage, metadata = run_theme_analysis(
        input_path=scrubbed_path,
        output_dir=output_dir,
        use_groq=False,
    )

    assert result.themes
    assert metadata.reviews_analyzed == 3
    assert usage.total_tokens == 0
