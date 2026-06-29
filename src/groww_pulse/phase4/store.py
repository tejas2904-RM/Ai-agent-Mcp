"""Persist Phase 4 insight selection artifacts."""

from __future__ import annotations

from pathlib import Path

from groww_pulse.phase3.models import GroqUsageEntry, GroqUsageLog
from groww_pulse.phase4.models import InsightSelectionResult


class InsightStore:
    """JSON store for insight selection outputs."""

    def __init__(self, analysis_dir: Path) -> None:
        self.analysis_dir = analysis_dir
        self.insights_path = analysis_dir / "insights.json"
        self.usage_path = analysis_dir / "groq_usage.json"

    def save_insights(self, result: InsightSelectionResult) -> Path:
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self.insights_path.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return self.insights_path

    def append_usage(self, entry: GroqUsageEntry) -> Path:
        log = self.load_usage()
        log.entries.append(entry)
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self.usage_path.write_text(
            log.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return self.usage_path

    def load_insights(self) -> InsightSelectionResult | None:
        if not self.insights_path.exists():
            return None
        return InsightSelectionResult.model_validate_json(
            self.insights_path.read_text(encoding="utf-8")
        )

    def load_usage(self) -> GroqUsageLog:
        if not self.usage_path.exists():
            return GroqUsageLog()
        return GroqUsageLog.model_validate_json(
            self.usage_path.read_text(encoding="utf-8")
        )
