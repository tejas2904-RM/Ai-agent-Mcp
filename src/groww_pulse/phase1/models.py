"""Normalized review schema and ingestion result types."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ReviewSource(str, Enum):
    APP_STORE = "app_store"
    PLAY_STORE = "play_store"


class NormalizedReview(BaseModel):
    """Unified review record used by downstream pipeline stages."""

    source: ReviewSource
    rating: int = Field(ge=1, le=5)
    title: str
    text: str
    date: date

    @field_validator("title", "text")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip()


class SkippedRow(BaseModel):
    source: ReviewSource
    row_number: int
    reason: str
    raw_preview: str | None = None


class IngestionReport(BaseModel):
    input_files: list[str]
    imported_raw: int = 0
    skipped: list[SkippedRow] = Field(default_factory=list)
    duplicates_removed: int = 0
    outside_window_removed: int = 0
    too_short_removed: int = 0
    non_english_removed: int = 0
    normalized_count: int = 0
    window_weeks: int = 0
    window_start: date | None = None
    window_end: date | None = None
    output_path: str | None = None

    @property
    def skip_count(self) -> int:
        return len(self.skipped)
