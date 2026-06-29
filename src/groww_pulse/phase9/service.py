"""Build PII-safe API payloads from analysis artifacts."""

from __future__ import annotations

from groww_pulse.phase9.models import (
    DeliveryLinks,
    PulsePayload,
    RunSummary,
    ThemeSummary,
    WeekSummary,
)
from groww_pulse.phase9.repository import ArtifactRepository


class PulseNotFoundError(LookupError):
    """Raised when no pulse artifacts are available."""


class RunNotFoundError(LookupError):
    """Raised when a run id or week range cannot be resolved."""


def _theme_summaries(repo: ArtifactRepository) -> list[ThemeSummary]:
    themes = repo.load_themes()
    if themes is None:
        return []
    return [
        ThemeSummary(
            name=theme.name,
            summary=theme.summary,
            volume_signal=theme.volume_signal,
            sentiment_signal=theme.sentiment_signal,
            review_count=theme.review_count,
            avg_rating=theme.avg_rating,
            low_star_pct=theme.low_star_pct,
            severity_score=theme.severity_score,
        )
        for theme in themes.themes
    ]


def build_pulse_payload(repo: ArtifactRepository) -> PulsePayload:
    insights = repo.load_insights()
    note = repo.load_note()
    if insights is None or note is None:
        raise PulseNotFoundError("Latest pulse artifacts are not available")

    note_text = repo.load_note_text() or note.content
    doc = repo.load_doc_delivery()
    draft = repo.load_draft_delivery()
    run = repo.load_latest_run()

    return PulsePayload(
        week_range=note.week_range,
        title=note.title,
        note_content=note_text,
        word_count=note.word_count,
        top_themes=insights.top_themes,
        all_themes=_theme_summaries(repo),
        quotes=insights.quotes,
        action_ideas=insights.action_ideas,
        delivery=DeliveryLinks(
            document_url=doc.document_url if doc else None,
            draft_id=draft.draft_id if draft else None,
        ),
        run_id=run.run_id if run else None,
        generated_at=note.generated_at,
    )


def list_weeks(repo: ArtifactRepository) -> list[WeekSummary]:
    weeks: dict[str, WeekSummary] = {}
    note = repo.load_note()
    if note is not None:
        weeks[note.week_range] = WeekSummary(
            week_range=note.week_range,
            title=note.title,
        )

    for run in repo.load_run_history().runs:
        if not run.week_range:
            continue
        weeks[run.week_range] = WeekSummary(
            week_range=run.week_range,
            title=f"Groww Weekly Review Pulse - {run.week_range}",
            status=run.status,
            run_id=run.run_id,
            completed_at=run.completed_at,
            document_url=run.artifacts.document_url,
        )

    latest = repo.load_latest_run()
    if latest is not None and latest.week_range:
        weeks[latest.week_range] = WeekSummary(
            week_range=latest.week_range,
            title=f"Groww Weekly Review Pulse - {latest.week_range}",
            status=latest.status,
            run_id=latest.run_id,
            completed_at=latest.completed_at,
            document_url=latest.artifacts.document_url,
        )

    return sorted(weeks.values(), key=lambda item: item.week_range, reverse=True)


def list_runs(repo: ArtifactRepository) -> list[RunSummary]:
    summaries: list[RunSummary] = []
    seen: set[str] = set()

    def append(run) -> None:
        if run.run_id in seen:
            return
        seen.add(run.run_id)
        summaries.append(
            RunSummary(
                run_id=run.run_id,
                week_range=run.week_range,
                status=run.status,
                started_at=run.started_at,
                completed_at=run.completed_at,
                is_rerun=run.is_rerun,
                delivery_skipped=run.delivery_skipped,
                note_word_count=run.artifacts.note_word_count,
                document_url=run.artifacts.document_url,
                draft_id=run.artifacts.draft_id,
            )
        )

    latest = repo.load_latest_run()
    if latest is not None:
        append(latest)
    for run in reversed(repo.load_run_history().runs):
        append(run)

    return summaries


def get_run_summary(repo: ArtifactRepository, run_id: str) -> RunSummary:
    run = repo.find_run(run_id)
    if run is None:
        raise RunNotFoundError(f"Run not found: {run_id}")
    return RunSummary(
        run_id=run.run_id,
        week_range=run.week_range,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        is_rerun=run.is_rerun,
        delivery_skipped=run.delivery_skipped,
        note_word_count=run.artifacts.note_word_count,
        document_url=run.artifacts.document_url,
        draft_id=run.artifacts.draft_id,
    )


def get_pulse_for_week(repo: ArtifactRepository, week_range: str) -> PulsePayload:
    latest = build_pulse_payload(repo)
    if latest.week_range == week_range:
        return latest
    run = repo.find_by_week(week_range)
    if run is None:
        raise RunNotFoundError(f"No pulse found for week: {week_range}")
    raise RunNotFoundError(
        f"Week {week_range} is recorded in run history but pulse artifacts are not archived per week yet"
    )
