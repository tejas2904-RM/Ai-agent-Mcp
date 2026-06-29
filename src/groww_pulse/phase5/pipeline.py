"""Phase 5 pipeline — weekly note generation via Groq Call #3."""

from __future__ import annotations

from pathlib import Path

from groww_pulse.config import DATA_DIR, Settings
from groww_pulse.phase3.groq_client import GroqClient, GroqClientProtocol, estimate_tokens
from groww_pulse.phase3.models import GroqUsageLog
from groww_pulse.phase3.store import AnalysisStore
from groww_pulse.phase4.store import InsightStore
from groww_pulse.phase5.models import (
    NOTE_MAX_CALL_TOKENS_IN_OUT,
    NOTE_MAX_INPUT_TOKENS,
    NOTE_RETRY_MAX_CALL_TOKENS_IN_OUT,
    WeeklyNoteResult,
    build_note_title,
    format_week_range,
)
from groww_pulse.phase5.note_agent import (
    build_note_generation_messages,
    generate_note_with_groq,
    render_fallback_note,
)
from groww_pulse.phase5.store import WeeklyNoteStore
from groww_pulse.phase5.validators import NoteValidationError, validate_note


class WeeklyNoteError(RuntimeError):
    """Raised when Phase 5 weekly note generation fails."""


def _resolve_week_range(analysis_path: Path) -> str:
    theme_store = AnalysisStore(
        analysis_path / "themes.json",
        analysis_path / "groq_usage.json",
        analysis_path / "run_metadata.json",
    )
    metadata = theme_store.load_metadata()
    if metadata is not None:
        stats = metadata.dataset_stats
        return format_week_range(stats.date_start, stats.date_end)

    themes = theme_store.load_themes()
    if themes is not None:
        stats = themes.dataset_stats
        return format_week_range(stats.date_start, stats.date_end)

    raise WeeklyNoteError("Cannot determine week range; run Phase 3 first.")


def _append_usage(usage_path: Path, entry) -> GroqUsageLog:
    log = GroqUsageLog()
    if usage_path.exists():
        log = GroqUsageLog.model_validate_json(usage_path.read_text(encoding="utf-8"))
    log.entries.append(entry)
    usage_path.write_text(log.model_dump_json(indent=2), encoding="utf-8")
    return log


def run_weekly_note_generation(
    analysis_dir: Path | None = None,
    *,
    groq_client: GroqClientProtocol | None = None,
    use_groq: bool = True,
    allow_retry: bool = True,
) -> tuple[WeeklyNoteResult, GroqUsageLog]:
    settings = Settings()
    analysis_path = analysis_dir or (DATA_DIR / "analysis")
    usage_path = analysis_path / "groq_usage.json"

    insight_store = InsightStore(analysis_path)
    insights = insight_store.load_insights()
    if insights is None:
        raise FileNotFoundError(
            f"Insights not found at {analysis_path / 'insights.json'}. Run Phase 4 first."
        )

    week_range = _resolve_week_range(analysis_path)
    title = build_note_title(week_range)
    model = settings.groq_model
    groq_calls = 0
    content = ""
    usage_log = GroqUsageLog()
    if usage_path.exists():
        usage_log = GroqUsageLog.model_validate_json(usage_path.read_text(encoding="utf-8"))

    if use_groq:
        client = groq_client
        if client is None:
            if not settings.groq_api_key:
                raise WeeklyNoteError(
                    "GROQ_API_KEY is not set. Configure it in .env for note generation."
                )
            client = GroqClient(
                api_key=settings.groq_api_key,
                model=model,
                max_input_tokens=NOTE_MAX_INPUT_TOKENS,
                max_total_tokens=NOTE_MAX_CALL_TOKENS_IN_OUT,
            )

        messages = build_note_generation_messages(insights, week_range=week_range)
        estimated_input = estimate_tokens(
            "\n".join(message["content"] for message in messages)
        )
        if estimated_input > NOTE_MAX_INPUT_TOKENS:
            raise WeeklyNoteError(
                f"Call #3 input estimate ({estimated_input}) exceeds cap "
                f"({NOTE_MAX_INPUT_TOKENS})"
            )

        content, usage_entry = generate_note_with_groq(
            client,
            insights,
            week_range=week_range,
            model=model,
            retry=False,
        )
        groq_calls = 1
        usage_log = _append_usage(usage_path, usage_entry)

        validation = validate_note(content)
        if not validation.passed and allow_retry:
            retry_client = client
            if groq_client is None:
                retry_client = GroqClient(
                    api_key=settings.groq_api_key or "",
                    model=model,
                    max_input_tokens=NOTE_MAX_INPUT_TOKENS,
                    max_total_tokens=NOTE_RETRY_MAX_CALL_TOKENS_IN_OUT,
                )
            feedback = "; ".join(validation.errors)
            content, retry_entry = generate_note_with_groq(
                retry_client,
                insights,
                week_range=week_range,
                model=model,
                retry=True,
                validation_feedback=feedback,
            )
            groq_calls = 2
            usage_log = _append_usage(usage_path, retry_entry)
    else:
        content = render_fallback_note(insights, week_range=week_range)

    validation = validate_note(content)
    if not validation.passed:
        raise NoteValidationError(
            "Weekly note failed validation: " + "; ".join(validation.errors)
        )

    result = WeeklyNoteResult(
        model=model,
        week_range=week_range,
        title=title,
        content=content,
        word_count=validation.word_count,
        validation_passed=True,
        groq_calls=groq_calls,
    )
    WeeklyNoteStore(analysis_path).save(result)
    return result, usage_log
