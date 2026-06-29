"""Phase 5 weekly note models."""

from __future__ import annotations

from datetime import date, datetime, timezone

from pydantic import BaseModel, Field

PRODUCT_NAME = "Groww"
MAX_WORD_COUNT = 250
NOTE_MAX_INPUT_TOKENS = 900
NOTE_MAX_CALL_TOKENS_IN_OUT = 1_100
NOTE_RETRY_MAX_CALL_TOKENS_IN_OUT = 1_100
NOTE_GENERATION_MAX_TOKENS = 400
NOTE_RETRY_MAX_TOKENS = 400

SECTION_THEMES = "top 3 themes"
SECTION_QUOTES = "user quotes"
SECTION_ACTIONS = "action ideas"


class WeeklyNoteResult(BaseModel):
    version: int = 1
    model: str
    week_range: str
    title: str
    content: str
    word_count: int
    validation_passed: bool
    groq_calls: int = 1
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NoteValidationResult(BaseModel):
    passed: bool
    word_count: int
    word_count_ok: bool
    sections_ok: bool
    pii_ok: bool
    scannable_ok: bool
    theme_items: int = 0
    quote_items: int = 0
    action_items: int = 0
    errors: list[str] = Field(default_factory=list)


def format_week_range(date_start: date, date_end: date) -> str:
    if date_start.year == date_end.year:
        if date_start.month == date_end.month:
            return f"{date_start.strftime('%b %d')} - {date_end.strftime('%d, %Y')}"
        return f"{date_start.strftime('%b %d')} - {date_end.strftime('%b %d, %Y')}"
    return f"{date_start.strftime('%b %d, %Y')} - {date_end.strftime('%b %d, %Y')}"


def build_note_title(week_range: str) -> str:
    return f"{PRODUCT_NAME} Weekly Review Pulse - {week_range}"
