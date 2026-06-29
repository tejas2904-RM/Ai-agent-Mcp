"""Phase 8 pipeline — end-to-end weekly Groww Review Pulse orchestration."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from groww_pulse.config import DATA_DIR, Settings
from groww_pulse.phase1.fetch_reviews import FetchReport, fetch_and_save_reviews
from groww_pulse.phase1.models import IngestionReport
from groww_pulse.phase1.pipeline import ingest_reviews
from groww_pulse.phase2.models import ScrubReport
from groww_pulse.phase2.pipeline import PiiScrubbingError, scrub_reviews
from groww_pulse.phase3.groq_client import GroqClientProtocol
from groww_pulse.phase3.models import GroqUsageLog
from groww_pulse.phase3.pipeline import ThemeAnalysisError, run_theme_analysis
from groww_pulse.phase4.pipeline import InsightSelectionError, run_insight_selection
from groww_pulse.phase5.models import WeeklyNoteResult
from groww_pulse.phase5.pipeline import WeeklyNoteError, run_weekly_note_generation
from groww_pulse.phase5.validators import validate_note
from groww_pulse.phase6.docs_client import DocsClientProtocol
from groww_pulse.phase6.models import DocDeliveryResult
from groww_pulse.phase6.pipeline import DocsDeliveryError, run_docs_delivery
from groww_pulse.phase7.gmail_client import GmailClientProtocol
from groww_pulse.phase7.models import DraftDeliveryResult
from groww_pulse.phase7.pipeline import GmailDeliveryError, run_gmail_delivery
from groww_pulse.phase8.models import (
    PhaseResult,
    RunArtifacts,
    WeeklyRunLog,
    find_successful_run_for_week,
    week_range_from_metadata,
)
from groww_pulse.phase8.retry import retry_call
from groww_pulse.phase8.store import RunLogStore


class WeeklyPulseError(RuntimeError):
    """Raised when the end-to-end weekly pulse workflow fails."""


def _record_phase(
    run_log: WeeklyRunLog,
    *,
    phase: int,
    name: str,
    started: float,
    status: str = "success",
    message: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    run_log.phases.append(
        PhaseResult(
            phase=phase,
            name=name,
            status=status,  # type: ignore[arg-type]
            duration_ms=int((time.perf_counter() - started) * 1000),
            message=message,
            details=details or {},
        )
    )


def _run_phase(
    run_log: WeeklyRunLog,
    *,
    phase: int,
    name: str,
    action: Callable[[], Any],
    retry: bool = False,
) -> Any:
    started = time.perf_counter()
    try:
        if retry:
            result = retry_call(action, label=name)
        else:
            result = action()
    except Exception as exc:
        _record_phase(
            run_log,
            phase=phase,
            name=name,
            started=started,
            status="failed",
            message=str(exc),
        )
        run_log.errors.append(f"Phase {phase} ({name}): {exc}")
        raise
    _record_phase(run_log, phase=phase, name=name, started=started)
    return result


def run_weekly_pulse(
    *,
    analysis_dir: Path | None = None,
    fresh_fetch: bool = True,
    use_groq: bool = True,
    deliver: bool = True,
    force_delivery: bool = False,
    reference_date: date | None = None,
    groq_client: GroqClientProtocol | None = None,
    docs_client: DocsClientProtocol | None = None,
    gmail_client: GmailClientProtocol | None = None,
    fetch_reviews_fn: Callable[..., FetchReport] | None = None,
    ingest_reviews_fn: Callable[..., tuple[Any, IngestionReport]] | None = None,
) -> WeeklyRunLog:
    """Run Phases 1-7: fresh ingestion through Gmail draft delivery."""
    settings = Settings()
    analysis_path = analysis_dir or settings.analysis_data_dir
    run_log = WeeklyRunLog(fresh_fetch=fresh_fetch)
    store = RunLogStore(analysis_path)
    store.save_latest(run_log)

    fetch_fn = fetch_reviews_fn or fetch_and_save_reviews
    ingest_fn = ingest_reviews_fn or ingest_reviews

    try:
        if fresh_fetch:
            fetch_report = _run_phase(
                run_log,
                phase=1,
                name="fetch_reviews",
                action=lambda: fetch_fn(reference_date=reference_date),
                retry=True,
            )
            run_log.phases[-1].details = {
                "app_store_saved": fetch_report.app_store_saved,
                "play_store_saved": fetch_report.play_store_saved,
            }
        else:
            _record_phase(
                run_log,
                phase=1,
                name="fetch_reviews",
                started=time.perf_counter(),
                status="skipped",
                message="fresh_fetch=False",
            )

        _, ingestion_report = _run_phase(
            run_log,
            phase=1,
            name="ingest_reviews",
            action=lambda: ingest_fn(reference_date=reference_date),
        )
        run_log.artifacts.normalized_count = ingestion_report.normalized_count
        run_log.phases[-1].details = {
            "normalized_count": ingestion_report.normalized_count,
            "duplicates_removed": ingestion_report.duplicates_removed,
        }

        _, scrub_report = _run_phase(
            run_log,
            phase=2,
            name="pii_scrub",
            action=scrub_reviews,
        )
        run_log.artifacts.scrubbed_count = scrub_report.output_count

        theme_result, usage_log, metadata = _run_phase(
            run_log,
            phase=3,
            name="theme_analysis",
            action=lambda: run_theme_analysis(
                use_groq=use_groq,
                groq_client=groq_client,
                output_dir=analysis_path,
            ),
        )
        week_range = week_range_from_metadata(metadata)
        run_log.week_range = week_range
        run_log.artifacts.theme_count = len(theme_result.themes)

        prior = find_successful_run_for_week(store.load_history(), week_range)
        run_log.is_rerun = prior is not None
        skip_delivery = (
            deliver
            and not force_delivery
            and prior is not None
            and prior.artifacts.document_url
            and prior.artifacts.draft_id
        )

        _run_phase(
            run_log,
            phase=4,
            name="insight_selection",
            action=lambda: run_insight_selection(
                analysis_dir=analysis_path,
                use_groq=use_groq,
                groq_client=groq_client,
            ),
        )

        note_result = _run_phase(
            run_log,
            phase=5,
            name="weekly_note",
            action=lambda: run_weekly_note_generation(
                analysis_dir=analysis_path,
                use_groq=use_groq,
                groq_client=groq_client,
            )[0],
        )
        run_log.artifacts.note_word_count = note_result.word_count

        validation = validate_note(note_result.content)
        if not validation.passed:
            raise WeeklyPulseError(
                f"Weekly note failed validation: {', '.join(validation.errors)}"
            )

        usage_log = _refresh_usage_log(analysis_path)
        run_log.artifacts.groq_calls = len(usage_log.entries)
        run_log.artifacts.groq_total_tokens = usage_log.total_tokens

        doc_result: DocDeliveryResult | None = None
        draft_result: DraftDeliveryResult | None = None

        if deliver and skip_delivery:
            run_log.delivery_skipped = True
            run_log.artifacts.document_url = prior.artifacts.document_url
            run_log.artifacts.draft_id = prior.artifacts.draft_id
            _record_phase(
                run_log,
                phase=6,
                name="google_doc_delivery",
                started=time.perf_counter(),
                status="skipped",
                message=f"Already delivered for week {week_range}",
            )
            _record_phase(
                run_log,
                phase=7,
                name="gmail_draft_delivery",
                started=time.perf_counter(),
                status="skipped",
                message=f"Already delivered for week {week_range}",
            )
        elif deliver:
            doc_result = _run_phase(
                run_log,
                phase=6,
                name="google_doc_delivery",
                action=lambda: run_docs_delivery(
                    analysis_dir=analysis_path,
                    docs_client=docs_client,
                ),
                retry=True,
            )
            run_log.artifacts.document_url = doc_result.document_url

            draft_result = _run_phase(
                run_log,
                phase=7,
                name="gmail_draft_delivery",
                action=lambda: run_gmail_delivery(
                    analysis_dir=analysis_path,
                    gmail_client=gmail_client,
                ),
                retry=True,
            )
            run_log.artifacts.draft_id = draft_result.draft_id
        else:
            _record_phase(
                run_log,
                phase=6,
                name="google_doc_delivery",
                started=time.perf_counter(),
                status="skipped",
                message="deliver=False",
            )
            _record_phase(
                run_log,
                phase=7,
                name="gmail_draft_delivery",
                started=time.perf_counter(),
                status="skipped",
                message="deliver=False",
            )

        run_log.status = "success"
    except (
        WeeklyPulseError,
        ThemeAnalysisError,
        InsightSelectionError,
        WeeklyNoteError,
        PiiScrubbingError,
        DocsDeliveryError,
        GmailDeliveryError,
        FileNotFoundError,
        OSError,
    ) as exc:
        run_log.status = "failed"
        if not run_log.errors:
            run_log.errors.append(str(exc))
        store.save_latest(run_log)
        store.append_history(run_log)
        raise WeeklyPulseError(str(exc)) from exc
    except Exception as exc:
        run_log.status = "failed"
        run_log.errors.append(str(exc))
        store.save_latest(run_log)
        store.append_history(run_log)
        raise

    from datetime import datetime, timezone

    run_log.completed_at = datetime.now(timezone.utc)
    store.save_latest(run_log)
    store.append_history(run_log)
    return run_log


def _refresh_usage_log(analysis_path: Path) -> GroqUsageLog:
    from groww_pulse.phase3.store import AnalysisStore

    store = AnalysisStore(
        analysis_path / "themes.json",
        analysis_path / "groq_usage.json",
        analysis_path / "run_metadata.json",
    )
    return store.load_usage()
