"""Phase 4 insight selection models."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from groww_pulse.phase3.models import ReviewSample, SentimentSignal, VolumeSignal

TOP_THEME_COUNT = 3
QUOTE_COUNT = 3
ACTION_IDEA_COUNT = 3
INSIGHT_MAX_SAMPLES_PER_THEME = 8
INSIGHT_SAMPLE_FALLBACKS = (6, 4, 3)
INSIGHT_SAMPLE_TEXT_CHARS = 120
INSIGHT_MAX_INPUT_TOKENS = 1_500
INSIGHT_MAX_CALL_TOKENS_IN_OUT = 1_800
INSIGHT_SELECTION_MAX_TOKENS = 600
TPM_COOLDOWN_SECONDS = 3


class TopThemeInsight(BaseModel):
    rank: int = Field(ge=1, le=3)
    name: str
    summary: str
    volume_signal: VolumeSignal
    sentiment_signal: SentimentSignal
    severity_score: float
    review_count: int
    avg_rating: float
    low_star_pct: float


class TraceableQuote(BaseModel):
    text: str
    review_id: int
    theme_name: str
    rating: int = Field(ge=1, le=5)
    source: str


class ActionIdea(BaseModel):
    theme_name: str
    idea: str


class InsightSelectionResult(BaseModel):
    version: int = 1
    model: str
    top_themes: list[TopThemeInsight] = Field(default_factory=list)
    quotes: list[TraceableQuote] = Field(default_factory=list)
    action_ideas: list[ActionIdea] = Field(default_factory=list)
    allowed_sample_ids: list[int] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ThemeInsightPacket(BaseModel):
    rank: int
    theme: TopThemeInsight
    samples: list[ReviewSample] = Field(default_factory=list)
