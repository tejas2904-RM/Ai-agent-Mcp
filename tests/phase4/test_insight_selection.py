"""Phase 4 insight selection tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from groww_pulse.phase1.models import NormalizedReview, ReviewSource
from groww_pulse.phase1.store import ReviewStore
from groww_pulse.phase2.pipeline import scrub_reviews
from groww_pulse.phase3.models import GroqUsageEntry
from groww_pulse.phase3.pipeline import run_theme_analysis
from groww_pulse.phase4.models import TOP_THEME_COUNT
from groww_pulse.phase4.pipeline import run_insight_selection
from groww_pulse.phase4.selection import build_insight_packets, rank_top_themes
from groww_pulse.phase4.store import InsightStore
from groww_pulse.phase4.validators import quote_matches_sample, validate_insights


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
            model="llama-3.3-70b-versatile",
            estimated_input_tokens=1000,
            total_tokens=1100,
            max_tokens=800,
        )


class MockInsightGroqClient:
    def __init__(self, sample_text: str, review_id: int = 0) -> None:
        self.sample_text = sample_text
        self.review_id = review_id

    def chat_completion(self, **kwargs: Any) -> tuple[dict[str, Any], GroqUsageEntry]:
        _ = kwargs
        return {
            "top_themes": [
                {"rank": 1, "name": "Payments & withdrawals", "summary": "Withdrawal pain."},
                {"rank": 2, "name": "Trading & orders", "summary": "Order issues."},
                {"rank": 3, "name": "App UX & support", "summary": "Crash reports."},
            ],
            "quotes": [
                {
                    "text": self.sample_text,
                    "review_id": self.review_id,
                    "theme_name": "Payments & withdrawals",
                },
                {
                    "text": self.sample_text,
                    "review_id": self.review_id,
                    "theme_name": "Trading & orders",
                },
                {
                    "text": self.sample_text,
                    "review_id": self.review_id,
                    "theme_name": "App UX & support",
                },
            ],
            "action_ideas": [
                {
                    "theme_name": "Payments & withdrawals",
                    "idea": "Audit withdrawal SLA and surface live status in-app.",
                },
                {
                    "theme_name": "Trading & orders",
                    "idea": "Improve order execution reliability during market open.",
                },
                {
                    "theme_name": "App UX & support",
                    "idea": "Fix crash regressions after app updates and login flow.",
                },
            ],
        }, GroqUsageEntry(
            call_id="phase4_insight_selection",
            phase=4,
            purpose="insight_selection",
            model="llama-3.3-70b-versatile",
            estimated_input_tokens=900,
            total_tokens=1200,
            max_tokens=600,
        )


def _prepare_scrubbed(tmp_path: Path, reviews: list[NormalizedReview]) -> Path:
    input_path = tmp_path / "normalized.json"
    scrubbed_path = tmp_path / "scrubbed.json"
    report_path = tmp_path / "report.json"
    ReviewStore(input_path).save(reviews)
    scrub_reviews(
        input_path=input_path,
        output_path=scrubbed_path,
        report_path=report_path,
    )
    return scrubbed_path


def test_rank_top_themes_by_severity(tmp_path: Path) -> None:
    reviews = [
        _review("withdrawal issue", rating=1),
        _review("order failed", rating=2),
        _review("app crash on login", rating=2),
        _review("sip works well", rating=5),
        _review("kyc stuck", rating=1),
        _review("great app", rating=5),
    ]
    scrubbed_path = _prepare_scrubbed(tmp_path, reviews)
    analysis_dir = tmp_path / "analysis"
    run_theme_analysis(
        input_path=scrubbed_path,
        output_dir=analysis_dir,
        groq_client=MockThemeGroqClient(),
    )
    from groww_pulse.phase3.store import AnalysisStore

    themes = AnalysisStore(
        analysis_dir / "themes.json",
        analysis_dir / "groq_usage.json",
        analysis_dir / "run_metadata.json",
    ).load_themes()
    assert themes is not None
    top = rank_top_themes(themes.themes)
    assert len(top) == TOP_THEME_COUNT
    assert top[0].severity_score >= top[1].severity_score >= top[2].severity_score


def test_pipeline_persists_insights_with_mock_groq(tmp_path: Path) -> None:
    quote_text = "Withdrawal still pending to my bank account for five days"
    reviews = [
        _review(quote_text, rating=1),
        _review("Order execution failed again during market open", rating=2),
        _review("App crashes after latest update and login fails", rating=2),
        _review("SIP in mutual fund works smoothly", rating=5),
        _review("KYC verification is stuck for weeks", rating=2),
        _review("Excellent overall investing experience on Groww", rating=5),
    ]
    scrubbed_path = _prepare_scrubbed(tmp_path, reviews)
    analysis_dir = tmp_path / "analysis"

    run_theme_analysis(
        input_path=scrubbed_path,
        output_dir=analysis_dir,
        groq_client=MockThemeGroqClient(),
    )
    from groww_pulse.phase3.store import AnalysisStore

    theme_store = AnalysisStore(
        analysis_dir / "themes.json",
        analysis_dir / "groq_usage.json",
        analysis_dir / "run_metadata.json",
    )
    themes = theme_store.load_themes()
    assert themes is not None
    packets = build_insight_packets(themes)
    sample_id = packets[0].samples[0].id
    sample_text = packets[0].samples[0].text

    result, usage = run_insight_selection(
        analysis_dir=analysis_dir,
        groq_client=MockInsightGroqClient(sample_text, sample_id),
        tpm_cooldown=False,
    )

    assert len(result.top_themes) == 3
    assert len(result.quotes) == 3
    assert len(result.action_ideas) == 3
    assert any(entry.phase == 4 for entry in usage.entries)

    store = InsightStore(analysis_dir)
    reloaded = store.load_insights()
    assert reloaded is not None
    validate_insights(reloaded, [sample for packet in packets for sample in packet.samples])


def test_quote_must_match_sample_verbatim() -> None:
    from groww_pulse.phase3.models import ReviewSample

    sample = ReviewSample(
        id=1,
        rating=1,
        date=date(2026, 6, 1),
        source=ReviewSource.PLAY_STORE,
        title="Issue",
        text="Withdrawal still pending to my bank account",
    )
    assert quote_matches_sample("Withdrawal still pending", sample)
    assert not quote_matches_sample("Completely invented quote", sample)


def test_fallback_insights_without_groq(tmp_path: Path) -> None:
    reviews = [
        _review("withdrawal issue with bank transfer", rating=1),
        _review("order failed during trading", rating=2),
        _review("app crash on login", rating=2),
        _review("sip investment good", rating=5),
        _review("kyc pending", rating=2),
        _review("nice app", rating=5),
    ]
    scrubbed_path = _prepare_scrubbed(tmp_path, reviews)
    analysis_dir = tmp_path / "analysis"
    run_theme_analysis(
        input_path=scrubbed_path,
        output_dir=analysis_dir,
        groq_client=MockThemeGroqClient(),
    )

    result, usage = run_insight_selection(
        analysis_dir=analysis_dir,
        use_groq=False,
        tpm_cooldown=False,
    )

    assert len(result.top_themes) == 3
    assert len(result.quotes) == 3
    assert len(result.action_ideas) == 3
    assert usage.entries
