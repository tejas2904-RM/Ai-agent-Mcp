"""Deterministic theme ranking and sample selection for Phase 4."""

from __future__ import annotations

from groww_pulse.phase3.models import RefinedTheme, ReviewSample, ThemePacket, ThemeAnalysisResult
from groww_pulse.phase4.models import (
    INSIGHT_MAX_SAMPLES_PER_THEME,
    TOP_THEME_COUNT,
    ThemeInsightPacket,
    TopThemeInsight,
)


def rank_top_themes(
    themes: list[RefinedTheme],
    *,
    count: int = TOP_THEME_COUNT,
) -> list[RefinedTheme]:
    ranked = sorted(themes, key=lambda theme: theme.severity_score, reverse=True)
    if len(ranked) < count:
        raise ValueError(f"Need at least {count} themes, got {len(ranked)}")
    return ranked[:count]


def _to_top_theme_insight(theme: RefinedTheme, rank: int) -> TopThemeInsight:
    return TopThemeInsight(
        rank=rank,
        name=theme.name,
        summary=theme.summary,
        volume_signal=theme.volume_signal,
        sentiment_signal=theme.sentiment_signal,
        severity_score=theme.severity_score,
        review_count=theme.review_count,
        avg_rating=theme.avg_rating,
        low_star_pct=theme.low_star_pct,
    )


def collect_samples_for_theme(
    theme: RefinedTheme,
    seed_packets: list[ThemePacket],
    *,
    max_samples: int = INSIGHT_MAX_SAMPLES_PER_THEME,
) -> list[ReviewSample]:
    packets_by_key = {packet.theme_key: packet for packet in seed_packets}
    collected: list[ReviewSample] = []
    seen_ids: set[int] = set()

    for theme_key in theme.merged_from:
        packet = packets_by_key.get(theme_key)
        if packet is None:
            continue
        for sample in packet.samples:
            if sample.id in seen_ids:
                continue
            collected.append(sample)
            seen_ids.add(sample.id)
            if len(collected) >= max_samples:
                return collected

    return collected[:max_samples]


def build_insight_packets(
    theme_result: ThemeAnalysisResult,
    *,
    max_samples_per_theme: int = INSIGHT_MAX_SAMPLES_PER_THEME,
) -> list[ThemeInsightPacket]:
    top_themes = rank_top_themes(theme_result.themes)
    packets: list[ThemeInsightPacket] = []
    for rank, theme in enumerate(top_themes, start=1):
        samples = collect_samples_for_theme(
            theme,
            theme_result.seed_packets,
            max_samples=max_samples_per_theme,
        )
        packets.append(
            ThemeInsightPacket(
                rank=rank,
                theme=_to_top_theme_insight(theme, rank),
                samples=samples,
            )
        )
    return packets


def flatten_allowed_samples(packets: list[ThemeInsightPacket]) -> list[ReviewSample]:
    seen: set[int] = set()
    samples: list[ReviewSample] = []
    for packet in packets:
        for sample in packet.samples:
            if sample.id in seen:
                continue
            samples.append(sample)
            seen.add(sample.id)
    return samples
