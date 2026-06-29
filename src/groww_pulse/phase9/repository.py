"""Read PII-safe analysis artifacts for the Phase 9 API."""

from __future__ import annotations

from pathlib import Path

from groww_pulse.phase3.models import ThemeAnalysisResult
from groww_pulse.phase3.store import AnalysisStore
from groww_pulse.phase4.models import InsightSelectionResult
from groww_pulse.phase4.store import InsightStore
from groww_pulse.phase5.models import WeeklyNoteResult
from groww_pulse.phase5.store import WeeklyNoteStore
from groww_pulse.phase6.models import DocDeliveryResult
from groww_pulse.phase6.store import DocDeliveryStore
from groww_pulse.phase7.models import DraftDeliveryResult
from groww_pulse.phase7.store import DraftDeliveryStore
from groww_pulse.phase8.models import RunHistory, WeeklyRunLog
from groww_pulse.phase8.store import RunLogStore


class ArtifactRepository:
    """Load pipeline outputs from the API data directory."""

    ARTIFACT_NAMES = (
        "themes.json",
        "insights.json",
        "weekly_note.json",
        "weekly_note.md",
        "weekly_run.json",
        "run_history.json",
        "doc_delivery.json",
        "draft_delivery.json",
        "run_metadata.json",
        "groq_usage.json",
    )

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def has_latest_pulse(self) -> bool:
        return (self.data_dir / "insights.json").exists() and (
            self.data_dir / "weekly_note.json"
        ).exists()

    def load_insights(self) -> InsightSelectionResult | None:
        return InsightStore(self.data_dir).load_insights()

    def load_note(self) -> WeeklyNoteResult | None:
        return WeeklyNoteStore(self.data_dir).load_result()

    def load_note_text(self) -> str | None:
        return WeeklyNoteStore(self.data_dir).load_note_text()

    def load_themes(self) -> ThemeAnalysisResult | None:
        store = AnalysisStore(
            self.data_dir / "themes.json",
            self.data_dir / "groq_usage.json",
            self.data_dir / "run_metadata.json",
        )
        return store.load_themes()

    def load_doc_delivery(self) -> DocDeliveryResult | None:
        return DocDeliveryStore(self.data_dir).load()

    def load_draft_delivery(self) -> DraftDeliveryResult | None:
        return DraftDeliveryStore(self.data_dir).load()

    def load_latest_run(self) -> WeeklyRunLog | None:
        return RunLogStore(self.data_dir).load_latest()

    def load_run_history(self) -> RunHistory:
        return RunLogStore(self.data_dir).load_history()

    def find_run(self, run_id: str) -> WeeklyRunLog | None:
        latest = self.load_latest_run()
        if latest is not None and latest.run_id == run_id:
            return latest
        for run in self.load_run_history().runs:
            if run.run_id == run_id:
                return run
        return None

    def find_by_week(self, week_range: str) -> WeeklyRunLog | None:
        latest = self.load_latest_run()
        if latest is not None and latest.week_range == week_range:
            return latest
        for run in reversed(self.load_run_history().runs):
            if run.week_range == week_range:
                return run
        return None
