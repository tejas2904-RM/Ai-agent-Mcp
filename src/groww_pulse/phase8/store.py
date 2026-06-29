"""Persist Phase 8 run logs and history."""

from __future__ import annotations

from pathlib import Path

from groww_pulse.phase8.models import RunHistory, WeeklyRunLog


class RunLogStore:
    def __init__(self, analysis_dir: Path) -> None:
        self.analysis_dir = analysis_dir
        self.latest_path = analysis_dir / "weekly_run.json"
        self.history_path = analysis_dir / "run_history.json"

    def save_latest(self, run_log: WeeklyRunLog) -> Path:
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self.latest_path.write_text(run_log.model_dump_json(indent=2), encoding="utf-8")
        return self.latest_path

    def load_latest(self) -> WeeklyRunLog | None:
        if not self.latest_path.exists():
            return None
        return WeeklyRunLog.model_validate_json(
            self.latest_path.read_text(encoding="utf-8")
        )

    def append_history(self, run_log: WeeklyRunLog) -> Path:
        history = self.load_history()
        history.runs.append(run_log)
        self.history_path.write_text(history.model_dump_json(indent=2), encoding="utf-8")
        return self.history_path

    def load_history(self) -> RunHistory:
        if not self.history_path.exists():
            return RunHistory()
        return RunHistory.model_validate_json(
            self.history_path.read_text(encoding="utf-8")
        )
