"""Deterministic pre-LLM aggregation for Phase 3."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from groww_pulse.phase1.models import NormalizedReview, ReviewSource
from groww_pulse.phase3.buckets import (
    GENERAL_THEME_KEY,
    SEED_THEMES,
    match_theme_key,
    theme_name_for_key,
)
from groww_pulse.phase3.models import (
    BucketAssignment,
    DatasetStats,
    RatingMix,
    REVIEW_CAP,
    ReviewSample,
    SourceSplit,
    ThemePacket,
)


@dataclass(frozen=True)
class IndexedReview:
    review_id: int
    review: NormalizedReview


def cap_reviews(
    reviews: list[NormalizedReview],
    *,
    max_reviews: int = REVIEW_CAP,
) -> tuple[list[IndexedReview], int]:
    """Keep the most recent reviews up to the cap."""
    sorted_reviews = sorted(reviews, key=lambda review: review.date, reverse=True)
    kept = sorted_reviews[:max_reviews]
    indexed = [
        IndexedReview(review_id=index, review=review)
        for index, review in enumerate(kept)
    ]
    dropped = max(0, len(reviews) - len(kept))
    return indexed, dropped


def assign_buckets(
    indexed_reviews: list[IndexedReview],
) -> tuple[dict[str, list[IndexedReview]], list[BucketAssignment]]:
    buckets: dict[str, list[IndexedReview]] = defaultdict(list)
    assignments: list[BucketAssignment] = []

    for item in indexed_reviews:
        theme_key = match_theme_key(item.review)
        buckets[theme_key].append(item)
        assignments.append(BucketAssignment(review_id=item.review_id, theme_key=theme_key))

    return dict(buckets), assignments


def _source_split(reviews: list[IndexedReview]) -> SourceSplit:
    split = SourceSplit()
    for item in reviews:
        if item.review.source == ReviewSource.APP_STORE:
            split.app_store += 1
        else:
            split.play_store += 1
    return split


def _rating_mix(reviews: list[IndexedReview]) -> RatingMix:
    mix = RatingMix()
    for item in reviews:
        rating = item.review.rating
        setattr(mix, f"star_{rating}", getattr(mix, f"star_{rating}") + 1)
    return mix


def compute_dataset_stats(indexed_reviews: list[IndexedReview]) -> DatasetStats:
    if not indexed_reviews:
        raise ValueError("Cannot compute stats on an empty review set")

    ratings = [item.review.rating for item in indexed_reviews]
    low_star = sum(1 for rating in ratings if rating <= 2)
    dates = [item.review.date for item in indexed_reviews]

    return DatasetStats(
        review_count=len(indexed_reviews),
        rating_mix=_rating_mix(indexed_reviews),
        source_split=_source_split(indexed_reviews),
        date_start=min(dates),
        date_end=max(dates),
        avg_rating=round(sum(ratings) / len(ratings), 2),
        low_star_pct=round(100 * low_star / len(ratings), 1),
    )


def compute_severity_score(review_count: int, avg_rating: float, low_star_pct: float) -> float:
  """Higher score surfaces painful, high-volume themes first."""
  rating_penalty = max(0.0, 5.0 - avg_rating)
  return round(review_count * (low_star_pct / 100.0) * rating_penalty, 2)


def _bucket_stats(bucket: list[IndexedReview]) -> tuple[float, float]:
    ratings = [item.review.rating for item in bucket]
    avg_rating = round(sum(ratings) / len(ratings), 2)
    low_star_pct = round(
        100 * sum(1 for rating in ratings if rating <= 2) / len(ratings),
        1,
    )
    return avg_rating, low_star_pct


def _text_signature(review: NormalizedReview) -> str:
    return review.text.strip().lower()[:60]


def select_representative_samples(
    bucket: list[IndexedReview],
    *,
    max_samples: int,
) -> list[ReviewSample]:
    if not bucket:
        return []

    low = [item for item in bucket if item.review.rating <= 2]
    high = [item for item in bucket if item.review.rating >= 4]
    mid = [item for item in bucket if item.review.rating == 3]

    selected: list[IndexedReview] = []
    seen_signatures: set[str] = set()

    def pick(pool: list[IndexedReview], limit: int) -> None:
        for item in sorted(pool, key=lambda entry: len(entry.review.text), reverse=True):
            if len(selected) >= max_samples or limit <= 0:
                return
            signature = _text_signature(item.review)
            if signature in seen_signatures:
                continue
            selected.append(item)
            seen_signatures.add(signature)
            limit -= 1

    low_target = max_samples // 2
    high_target = max_samples - low_target
    pick(low, low_target)
    pick(high, high_target)
    if len(selected) < max_samples:
        pick(mid, max_samples - len(selected))
    if len(selected) < max_samples:
        for item in bucket:
            if len(selected) >= max_samples:
                break
            signature = _text_signature(item.review)
            if signature in seen_signatures:
                continue
            selected.append(item)
            seen_signatures.add(signature)

    return [
        ReviewSample(
            id=item.review_id,
            rating=item.review.rating,
            date=item.review.date,
            source=item.review.source,
            title=item.review.title,
            text=item.review.text,
        )
        for item in selected[:max_samples]
    ]


def ordered_theme_keys(buckets: dict[str, list[IndexedReview]]) -> list[str]:
    keys = [theme.key for theme in SEED_THEMES]
    if GENERAL_THEME_KEY in buckets:
        keys.append(GENERAL_THEME_KEY)
    return [key for key in keys if key in buckets]


def build_theme_packets(
    buckets: dict[str, list[IndexedReview]],
    *,
    samples_per_bucket: int,
) -> list[ThemePacket]:
    packets: list[ThemePacket] = []
    for theme_key in ordered_theme_keys(buckets):
        bucket = buckets[theme_key]
        avg_rating, low_star_pct = _bucket_stats(bucket)
        packets.append(
            ThemePacket(
                theme_key=theme_key,
                theme_name=theme_name_for_key(theme_key),
                review_count=len(bucket),
                avg_rating=avg_rating,
                low_star_pct=low_star_pct,
                source_split=_source_split(bucket),
                samples=select_representative_samples(bucket, max_samples=samples_per_bucket),
            )
        )
    return packets


def rebuild_packets_with_sample_cap(
    buckets: dict[str, list[IndexedReview]],
    samples_per_bucket: int,
) -> list[ThemePacket]:
    return build_theme_packets(buckets, samples_per_bucket=samples_per_bucket)

