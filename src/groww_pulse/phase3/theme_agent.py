"""Groq theme analysis agent (Call #1)."""

from __future__ import annotations

from typing import Any

from groww_pulse.phase3.aggregation import compute_severity_score
from groww_pulse.phase3.buckets import theme_name_for_key
from groww_pulse.phase3.groq_client import GroqClientProtocol, estimate_tokens
from groww_pulse.phase3.models import (
    DatasetStats,
    MAX_SAMPLE_TEXT_CHARS,
    MAX_THEMES,
    ReviewSample,
    RefinedTheme,
    SentimentSignal,
    THEME_ANALYSIS_MAX_TOKENS,
    ThemePacket,
    VolumeSignal,
)

SYSTEM_PROMPT = """You are a product insights analyst for Groww (Stocks, Mutual Funds & Gold).
You receive pre-aggregated review theme packets with stats and sample reviews.
Refine the seed buckets into at most 5 clear product themes.

Rules:
- Return JSON only.
- Merge overlapping themes and fold "general_experience" into the nearest real theme when appropriate.
- Never invent review text.
- Use the provided review_count, avg_rating, and low_star_pct from packets when reporting volume.
- Each theme needs: name, summary (one line), volume_signal, sentiment_signal, merged_from.
- volume_signal must be one of: high, medium, low.
- sentiment_signal must be one of: negative, mixed, positive.
- merged_from must list seed theme keys from the packets.
"""


def _compact_sample(sample: ReviewSample) -> dict[str, object]:
    text = sample.text
    if len(text) > MAX_SAMPLE_TEXT_CHARS:
        text = text[: MAX_SAMPLE_TEXT_CHARS - 3].rstrip() + "..."
    title = sample.title
    if len(title) > 80:
        title = title[:77].rstrip() + "..."
    payload = sample.model_dump(mode="json")
    payload["title"] = title
    payload["text"] = text
    return payload


def build_theme_analysis_messages(
    packets: list[ThemePacket],
    dataset_stats: DatasetStats,
) -> list[dict[str, str]]:
    packet_payload = [
        {
            "theme_key": packet.theme_key,
            "theme_name": packet.theme_name,
            "review_count": packet.review_count,
            "avg_rating": packet.avg_rating,
            "low_star_pct": packet.low_star_pct,
            "source_split": packet.source_split.model_dump(),
            "samples": [_compact_sample(sample) for sample in packet.samples],
        }
        for packet in packets
    ]
    user_content = (
        "Global dataset stats:\n"
        f"{dataset_stats.model_dump_json()}\n\n"
        "Seed theme packets:\n"
        f"{packet_payload}\n\n"
        "Return JSON with shape:\n"
        '{"themes":[{"name":"...","summary":"...","volume_signal":"high|medium|low",'
        '"sentiment_signal":"negative|mixed|positive","merged_from":["theme_key"],'
        '"review_count":0,"avg_rating":0.0,"low_star_pct":0.0}]}'
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def volume_signal_for(review_count: int, total_reviews: int) -> VolumeSignal:
    share = review_count / max(total_reviews, 1)
    if share >= 0.2:
        return "high"
    if share >= 0.08:
        return "medium"
    return "low"


def sentiment_signal_for(avg_rating: float, low_star_pct: float) -> SentimentSignal:
    if avg_rating < 3.0 or low_star_pct >= 50:
        return "negative"
    if avg_rating >= 4.0 and low_star_pct < 20:
        return "positive"
    return "mixed"


def _aggregate_packet_stats(
    merged_from: list[str],
    packets_by_key: dict[str, ThemePacket],
) -> tuple[int, float, float]:
    selected = [packets_by_key[key] for key in merged_from if key in packets_by_key]
    if not selected:
        return 0, 0.0, 0.0

    total_count = sum(packet.review_count for packet in selected)
    weighted_rating = sum(packet.avg_rating * packet.review_count for packet in selected)
    weighted_low = sum(packet.low_star_pct * packet.review_count for packet in selected)
    avg_rating = round(weighted_rating / total_count, 2)
    low_star_pct = round(weighted_low / total_count, 1)
    return total_count, avg_rating, low_star_pct


def normalize_llm_themes(
    llm_payload: dict[str, Any],
    packets: list[ThemePacket],
    dataset_stats: DatasetStats,
) -> list[RefinedTheme]:
    packets_by_key = {packet.theme_key: packet for packet in packets}
    raw_themes = llm_payload.get("themes", [])
    if not isinstance(raw_themes, list):
        raise ValueError("Groq themes payload must contain a list")

    refined: list[RefinedTheme] = []
    for item in raw_themes[:MAX_THEMES]:
        if not isinstance(item, dict):
            continue
        merged_from = item.get("merged_from") or []
        if not isinstance(merged_from, list):
            merged_from = []
        merged_from = [str(key) for key in merged_from if str(key) in packets_by_key]
        if not merged_from and packets_by_key:
            merged_from = [next(iter(packets_by_key))]

        review_count, avg_rating, low_star_pct = _aggregate_packet_stats(
            merged_from,
            packets_by_key,
        )
        if review_count == 0:
            continue

        name = str(item.get("name") or theme_name_for_key(merged_from[0]))
        summary = str(item.get("summary") or "User feedback theme")
        volume_signal = item.get("volume_signal")
        if volume_signal not in {"high", "medium", "low"}:
            volume_signal = volume_signal_for(review_count, dataset_stats.review_count)
        sentiment_signal = item.get("sentiment_signal")
        if sentiment_signal not in {"negative", "mixed", "positive"}:
            sentiment_signal = sentiment_signal_for(avg_rating, low_star_pct)

        refined.append(
            RefinedTheme(
                name=name,
                summary=summary,
                volume_signal=volume_signal,
                sentiment_signal=sentiment_signal,
                merged_from=merged_from,
                review_count=review_count,
                avg_rating=avg_rating,
                low_star_pct=low_star_pct,
                severity_score=compute_severity_score(
                    review_count,
                    avg_rating,
                    low_star_pct,
                ),
            )
        )

    refined.sort(key=lambda theme: theme.severity_score, reverse=True)
    return refined[:MAX_THEMES]


def analyze_themes_with_groq(
    client: GroqClientProtocol,
    packets: list[ThemePacket],
    dataset_stats: DatasetStats,
) -> tuple[list[RefinedTheme], Any]:
    messages = build_theme_analysis_messages(packets, dataset_stats)
    prompt_text = "\n".join(message["content"] for message in messages)
    estimated_input = estimate_tokens(prompt_text)

    payload, usage = client.chat_completion(
        messages=messages,
        max_tokens=THEME_ANALYSIS_MAX_TOKENS,
        call_id="phase3_theme_analysis",
        phase=3,
        purpose="theme_analysis",
        estimated_input_tokens=estimated_input,
        response_format={"type": "json_object"},
    )
    themes = normalize_llm_themes(payload, packets, dataset_stats)
    if not themes:
        raise ValueError("Groq returned no usable themes")
    return themes, usage
