"""Phase 3 pipeline — pre-LLM aggregation and Groq theme analysis."""

from __future__ import annotations

from pathlib import Path

from groww_pulse.config import DATA_DIR, Settings
from groww_pulse.phase2.store import ScrubbedReviewStore
from groww_pulse.phase3.aggregation import (
    assign_buckets,
    build_theme_packets,
    cap_reviews,
    compute_dataset_stats,
    rebuild_packets_with_sample_cap,
)
from groww_pulse.phase3.groq_client import GroqClient, GroqClientProtocol, estimate_tokens
from groww_pulse.phase3.models import (
    GroqUsageLog,
    MAX_INPUT_TOKENS,
    MAX_SAMPLES_DEFAULT,
    MAX_SAMPLES_FALLBACKS,
    REVIEW_CAP,
    RunMetadata,
    ThemeAnalysisResult,
)
from groww_pulse.phase3.store import AnalysisStore
from groww_pulse.phase3.theme_agent import (
    analyze_themes_with_groq,
    build_theme_analysis_messages,
    normalize_llm_themes,
    sentiment_signal_for,
    volume_signal_for,
)


class ThemeAnalysisError(RuntimeError):
    """Raised when Phase 3 theme analysis fails."""


def _estimate_call1_input_tokens(
    packets,
    dataset_stats,
) -> int:
    messages = build_theme_analysis_messages(packets, dataset_stats)
    text = "\n".join(message["content"] for message in messages)
    return estimate_tokens(text)


def _build_packets_within_budget(buckets, dataset_stats):
    packets = None
    samples_per_bucket = MAX_SAMPLES_DEFAULT
    estimated = 0

    for candidate in MAX_SAMPLES_FALLBACKS:
        packets = rebuild_packets_with_sample_cap(
            buckets,
            samples_per_bucket=candidate,
        )
        estimated = _estimate_call1_input_tokens(packets, dataset_stats)
        samples_per_bucket = candidate
        if estimated <= MAX_INPUT_TOKENS:
            break

    if packets is None or estimated > MAX_INPUT_TOKENS:
        raise ThemeAnalysisError(
            f"Call #1 input estimate ({estimated} tokens) exceeds cap ({MAX_INPUT_TOKENS}) "
            "even after reducing samples per bucket"
        )
    return packets, samples_per_bucket, estimated


def _fallback_themes_from_packets(packets, dataset_stats):
    """Deterministic themes when Groq is unavailable (tests/local dev)."""
    themes = []
    for packet in packets:
        themes.append(
            {
                "name": packet.theme_name,
                "summary": f"Users discuss {packet.theme_name.lower()} in recent reviews.",
                "volume_signal": volume_signal_for(
                    packet.review_count,
                    dataset_stats.review_count,
                ),
                "sentiment_signal": sentiment_signal_for(
                    packet.avg_rating,
                    packet.low_star_pct,
                ),
                "merged_from": [packet.theme_key],
                "review_count": packet.review_count,
                "avg_rating": packet.avg_rating,
                "low_star_pct": packet.low_star_pct,
            }
        )
    payload = {"themes": themes}
    refined = normalize_llm_themes(payload, packets, dataset_stats)
    return refined[:5]


def run_theme_analysis(
    input_path: Path | None = None,
    output_dir: Path | None = None,
    *,
    groq_client: GroqClientProtocol | None = None,
    use_groq: bool = True,
) -> tuple[ThemeAnalysisResult, GroqUsageLog, RunMetadata]:
    settings = Settings()
    scrubbed_path = input_path or (settings.scrubbed_data_dir / "groww_reviews.json")
    analysis_dir = output_dir or (DATA_DIR / "analysis")
    themes_path = analysis_dir / "themes.json"
    usage_path = analysis_dir / "groq_usage.json"
    metadata_path = analysis_dir / "run_metadata.json"

    if not scrubbed_path.exists():
        raise FileNotFoundError(
            f"Scrubbed reviews not found at {scrubbed_path}. Run Phase 2 first."
        )

    scrubbed_reviews = ScrubbedReviewStore(
        scrubbed_path,
        settings.scrubbed_data_dir / "pii_scrub_report.json",
    ).load_reviews()
    if not scrubbed_reviews:
        raise ThemeAnalysisError("Scrubbed review dataset is empty")

    indexed, dropped = cap_reviews(scrubbed_reviews, max_reviews=REVIEW_CAP)
    buckets, assignments = assign_buckets(indexed)
    dataset_stats = compute_dataset_stats(indexed)
    packets, samples_per_bucket, estimated_tokens = _build_packets_within_budget(
        buckets,
        dataset_stats,
    )

    metadata = RunMetadata(
        scrubbed_total=len(scrubbed_reviews),
        reviews_analyzed=len(indexed),
        reviews_dropped=dropped,
        samples_per_bucket=samples_per_bucket,
        dataset_stats=dataset_stats,
        bucket_counts={key: len(bucket) for key, bucket in buckets.items()},
        assignments=assignments,
        estimated_call1_input_tokens=estimated_tokens,
    )

    usage_log = GroqUsageLog()
    model = settings.groq_model

    if use_groq:
        client = groq_client
        if client is None:
            if not settings.groq_api_key:
                raise ThemeAnalysisError(
                    "GROQ_API_KEY is not set. Configure it in .env for live theme analysis."
                )
            client = GroqClient(
                api_key=settings.groq_api_key,
                model=model,
                max_input_tokens=MAX_INPUT_TOKENS,
            )
        themes, usage_entry = analyze_themes_with_groq(client, packets, dataset_stats)
        usage_log.entries.append(usage_entry)
    else:
        themes = _fallback_themes_from_packets(packets, dataset_stats)

    result = ThemeAnalysisResult(
        model=model,
        themes=themes,
        seed_packets=packets,
        dataset_stats=dataset_stats,
    )

    store = AnalysisStore(themes_path, usage_path, metadata_path)
    store.save(result, usage_log, metadata)
    return result, usage_log, metadata
