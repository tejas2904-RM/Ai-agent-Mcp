"""Phase 8 orchestration tests."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from groww_pulse.phase1.fetch_reviews import FetchReport
from groww_pulse.phase6.models import google_doc_url
from groww_pulse.phase1.pipeline import ingest_reviews
from groww_pulse.phase8.models import RunArtifacts, WeeklyRunLog
from groww_pulse.phase8.pipeline import run_weekly_pulse
from groww_pulse.phase8.retry import is_retryable_error, retry_call
from groww_pulse.phase8.store import RunLogStore


class MockDocsClient:
    def publish_weekly_note(self, *, title: str, content: str) -> dict[str, Any]:
        _ = title, content
        document_id = "orch-doc-001"
        return {
            "status": "success",
            "document_id": document_id,
            "document_url": google_doc_url(document_id),
        }


class MockGmailClient:
    def create_weekly_draft(self, *, to: str, subject: str, body: str) -> dict[str, Any]:
        _ = to, subject, body
        return {
            "status": "success",
            "draft_id": "orch-draft-001",
            "message": "Draft created",
        }


def _copy_sample_data(project_root: Path, tmp_path: Path) -> Path:
    sample_src = project_root / "data" / "sample"
    sample_dst = tmp_path / "sample"
    shutil.copytree(sample_src, sample_dst)
    return sample_dst


def test_retry_call_retries_transient_errors() -> None:
    attempts = {"count": 0}

    def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ConnectionError("temporary")
        return "ok"

    assert retry_call(flaky, label="flaky", delays=(0.0, 0.0)) == "ok"
    assert attempts["count"] == 3


def test_is_retryable_error() -> None:
    assert is_retryable_error(ConnectionError("reset"))
    assert not is_retryable_error(ValueError("bad input"))


def test_run_weekly_pulse_end_to_end_without_fetch(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sample_dir = _copy_sample_data(project_root, tmp_path)
    normalized_dir = tmp_path / "normalized"
    scrubbed_dir = tmp_path / "scrubbed"
    analysis_dir = tmp_path / "analysis"
    normalized_dir.mkdir()
    scrubbed_dir.mkdir()

    monkeypatch.setenv("SAMPLE_DATA_DIR", str(sample_dir))
    monkeypatch.setenv("NORMALIZED_DATA_DIR", str(normalized_dir))
    monkeypatch.setenv("SCRUBBED_DATA_DIR", str(scrubbed_dir))
    monkeypatch.setenv("ANALYSIS_DATA_DIR", str(analysis_dir))
    monkeypatch.setenv("GMAIL_RECIPIENT", "pulse@example.com")

    def fake_fetch(**_kwargs: Any) -> FetchReport:
        return FetchReport(app_store_saved=1, play_store_saved=1)

    run_log = run_weekly_pulse(
        analysis_dir=analysis_dir,
        fresh_fetch=False,
        use_groq=False,
        deliver=True,
        reference_date=date(2026, 6, 26),
        docs_client=MockDocsClient(),
        gmail_client=MockGmailClient(),
        fetch_reviews_fn=fake_fetch,
        ingest_reviews_fn=lambda **kwargs: ingest_reviews(
            input_dir=sample_dir,
            output_path=normalized_dir / "groww_reviews.json",
            **kwargs,
        ),
    )

    assert run_log.status == "success"
    assert run_log.week_range is not None
    assert run_log.artifacts.normalized_count and run_log.artifacts.normalized_count > 0
    assert run_log.artifacts.note_word_count is not None
    assert run_log.artifacts.document_url is not None
    assert run_log.artifacts.draft_id == "orch-draft-001"
    assert any(phase.name == "weekly_note" for phase in run_log.phases)

    reloaded = RunLogStore(analysis_dir).load_latest()
    assert reloaded is not None
    assert reloaded.run_id == run_log.run_id
    assert (analysis_dir / "weekly_note.md").exists()


def test_run_weekly_pulse_skips_duplicate_delivery(
    project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sample_dir = _copy_sample_data(project_root, tmp_path)
    normalized_dir = tmp_path / "normalized"
    scrubbed_dir = tmp_path / "scrubbed"
    analysis_dir = tmp_path / "analysis"
    normalized_dir.mkdir()
    scrubbed_dir.mkdir()

    monkeypatch.setenv("SAMPLE_DATA_DIR", str(sample_dir))
    monkeypatch.setenv("NORMALIZED_DATA_DIR", str(normalized_dir))
    monkeypatch.setenv("SCRUBBED_DATA_DIR", str(scrubbed_dir))
    monkeypatch.setenv("ANALYSIS_DATA_DIR", str(analysis_dir))
    monkeypatch.setenv("GMAIL_RECIPIENT", "pulse@example.com")

    kwargs = dict(
        analysis_dir=analysis_dir,
        fresh_fetch=False,
        use_groq=False,
        deliver=True,
        reference_date=date(2026, 6, 26),
        docs_client=MockDocsClient(),
        gmail_client=MockGmailClient(),
        ingest_reviews_fn=lambda **kw: ingest_reviews(
            input_dir=sample_dir,
            output_path=normalized_dir / "groww_reviews.json",
            **kw,
        ),
    )

    first = run_weekly_pulse(**kwargs)
    second = run_weekly_pulse(**kwargs)

    assert first.status == "success"
    assert second.status == "success"
    assert second.is_rerun is True
    assert second.delivery_skipped is True
    assert any(
        phase.name == "google_doc_delivery" and phase.status == "skipped"
        for phase in second.phases
    )

    history = RunLogStore(analysis_dir).load_history()
    assert len(history.runs) >= 2


def test_run_history_persists(project_root: Path, tmp_path: Path) -> None:
    analysis_dir = tmp_path / "analysis"
    store = RunLogStore(analysis_dir)
    run = WeeklyRunLog(
        week_range="Jun 01 - 07, 2026",
        status="success",
        artifacts=RunArtifacts(document_url="https://example.com/doc", draft_id="d1"),
    )
    store.save_latest(run)
    store.append_history(run)

    loaded = store.load_history()
    assert len(loaded.runs) == 1
    assert loaded.runs[0].week_range == "Jun 01 - 07, 2026"
