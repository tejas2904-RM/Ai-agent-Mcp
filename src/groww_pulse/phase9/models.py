"""Phase 9 API response models — PII-safe, no raw review corpus."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from groww_pulse.phase4.models import ActionIdea, TopThemeInsight, TraceableQuote


class ThemeSummary(BaseModel):
    name: str
    summary: str
    volume_signal: str
    sentiment_signal: str
    review_count: int
    avg_rating: float
    low_star_pct: float
    severity_score: float


class DeliveryLinks(BaseModel):
    document_url: str | None = None
    draft_id: str | None = None


class PulsePayload(BaseModel):
    week_range: str
    title: str
    note_content: str
    word_count: int
    top_themes: list[TopThemeInsight] = Field(default_factory=list)
    all_themes: list[ThemeSummary] = Field(default_factory=list)
    quotes: list[TraceableQuote] = Field(default_factory=list)
    action_ideas: list[ActionIdea] = Field(default_factory=list)
    delivery: DeliveryLinks = Field(default_factory=DeliveryLinks)
    run_id: str | None = None
    generated_at: datetime | None = None


class WeekSummary(BaseModel):
    week_range: str
    title: str
    status: str | None = None
    run_id: str | None = None
    completed_at: datetime | None = None
    document_url: str | None = None


class RunSummary(BaseModel):
    run_id: str
    week_range: str | None = None
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    is_rerun: bool = False
    delivery_skipped: bool = False
    note_word_count: int | None = None
    document_url: str | None = None
    draft_id: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "groww-pulse-api"
    data_dir: str
    has_latest_pulse: bool = False


class SyncResponse(BaseModel):
    status: str
    files_synced: list[str] = Field(default_factory=list)
