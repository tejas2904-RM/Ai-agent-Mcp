"""Phase 3 theme analysis models."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from groww_pulse.phase1.models import ReviewSource

REVIEW_CAP = 600
MAX_THEMES = 5
MAX_SAMPLES_DEFAULT = 8
MAX_SAMPLES_REDUCED = 6
MAX_SAMPLES_FALLBACKS = (8, 6, 4, 3)
MAX_SAMPLE_TEXT_CHARS = 280
MAX_INPUT_TOKENS = 3_500
MAX_CALL_TOKENS_IN_OUT = 6_000
THEME_ANALYSIS_MAX_TOKENS = 800


class ReviewSample(BaseModel):
    id: int
    rating: int = Field(ge=1, le=5)
    date: date
    source: ReviewSource
    title: str
    text: str


class SourceSplit(BaseModel):
    app_store: int = 0
    play_store: int = 0


class ThemePacket(BaseModel):
    theme_key: str
    theme_name: str
    review_count: int
    avg_rating: float
    low_star_pct: float
    source_split: SourceSplit
    samples: list[ReviewSample] = Field(default_factory=list)


class RatingMix(BaseModel):
    star_1: int = 0
    star_2: int = 0
    star_3: int = 0
    star_4: int = 0
    star_5: int = 0


class DatasetStats(BaseModel):
    review_count: int
    rating_mix: RatingMix
    source_split: SourceSplit
    date_start: date
    date_end: date
    avg_rating: float
    low_star_pct: float


class BucketAssignment(BaseModel):
    review_id: int
    theme_key: str


class RunMetadata(BaseModel):
    scrubbed_total: int
    review_cap: int = REVIEW_CAP
    reviews_analyzed: int
    reviews_dropped: int
    samples_per_bucket: int
    dataset_stats: DatasetStats
    bucket_counts: dict[str, int]
    assignments: list[BucketAssignment] = Field(default_factory=list)
    estimated_call1_input_tokens: int = 0
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


VolumeSignal = Literal["high", "medium", "low"]
SentimentSignal = Literal["negative", "mixed", "positive"]


class RefinedTheme(BaseModel):
    name: str
    summary: str
    volume_signal: VolumeSignal
    sentiment_signal: SentimentSignal
    merged_from: list[str] = Field(default_factory=list)
    review_count: int
    avg_rating: float
    low_star_pct: float
    severity_score: float


class ThemeAnalysisResult(BaseModel):
    version: int = 1
    model: str
    themes: list[RefinedTheme] = Field(default_factory=list)
    seed_packets: list[ThemePacket] = Field(default_factory=list)
    dataset_stats: DatasetStats
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GroqUsageEntry(BaseModel):
    call_id: str
    phase: int
    purpose: str
    model: str
    estimated_input_tokens: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    max_tokens: int = 0
    called_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GroqUsageLog(BaseModel):
    entries: list[GroqUsageEntry] = Field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return sum(entry.total_tokens for entry in self.entries)
