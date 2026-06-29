"""Phase 8 orchestration models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from groww_pulse.phase3.models import RunMetadata
from groww_pulse.phase5.models import format_week_range


class PhaseResult(BaseModel):
    phase: int
    name: str
    status: Literal["success", "failed", "skipped"]
    duration_ms: int = 0
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class RunArtifacts(BaseModel):
    normalized_count: int | None = None
    scrubbed_count: int | None = None
    theme_count: int | None = None
    note_word_count: int | None = None
    document_url: str | None = None
    draft_id: str | None = None
    groq_calls: int | None = None
    groq_total_tokens: int | None = None


class WeeklyRunLog(BaseModel):
    version: int = 1
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    week_range: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    status: Literal["running", "success", "failed"] = "running"
    is_rerun: bool = False
    delivery_skipped: bool = False
    fresh_fetch: bool = True
    phases: list[PhaseResult] = Field(default_factory=list)
    artifacts: RunArtifacts = Field(default_factory=RunArtifacts)
    errors: list[str] = Field(default_factory=list)


class RunHistory(BaseModel):
    version: int = 1
    runs: list[WeeklyRunLog] = Field(default_factory=list)


def week_range_from_metadata(metadata: RunMetadata) -> str:
    stats = metadata.dataset_stats
    return format_week_range(stats.date_start, stats.date_end)


def find_successful_run_for_week(
    history: RunHistory, week_range: str
) -> WeeklyRunLog | None:
    for run in reversed(history.runs):
        if run.week_range == week_range and run.status == "success":
            return run
    return None
