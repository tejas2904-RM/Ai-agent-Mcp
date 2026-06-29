"""Persist Phase 3 analysis artifacts."""

from __future__ import annotations

from pathlib import Path

from groww_pulse.phase3.models import GroqUsageLog, RunMetadata, ThemeAnalysisResult


class AnalysisStore:
    """JSON store for theme analysis outputs."""

    def __init__(
        self,
        themes_path: Path,
        usage_path: Path,
        metadata_path: Path,
    ) -> None:
        self.themes_path = themes_path
        self.usage_path = usage_path
        self.metadata_path = metadata_path

    def save(
        self,
        result: ThemeAnalysisResult,
        usage: GroqUsageLog,
        metadata: RunMetadata,
    ) -> tuple[Path, Path, Path]:
        self.themes_path.parent.mkdir(parents=True, exist_ok=True)
        self.themes_path.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )
        self.usage_path.write_text(
            usage.model_dump_json(indent=2),
            encoding="utf-8",
        )
        self.metadata_path.write_text(
            metadata.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return self.themes_path, self.usage_path, self.metadata_path

    def load_themes(self) -> ThemeAnalysisResult | None:
        if not self.themes_path.exists():
            return None
        return ThemeAnalysisResult.model_validate_json(
            self.themes_path.read_text(encoding="utf-8")
        )

    def load_usage(self) -> GroqUsageLog:
        if not self.usage_path.exists():
            return GroqUsageLog()
        return GroqUsageLog.model_validate_json(
            self.usage_path.read_text(encoding="utf-8")
        )

    def load_metadata(self) -> RunMetadata | None:
        if not self.metadata_path.exists():
            return None
        return RunMetadata.model_validate_json(
            self.metadata_path.read_text(encoding="utf-8")
        )
