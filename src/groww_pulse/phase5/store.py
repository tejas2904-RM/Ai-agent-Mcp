"""Persist Phase 5 weekly note artifacts."""

from __future__ import annotations

from pathlib import Path

from groww_pulse.phase5.models import WeeklyNoteResult


class WeeklyNoteStore:
    """Store for weekly note markdown and metadata."""

    def __init__(self, analysis_dir: Path) -> None:
        self.analysis_dir = analysis_dir
        self.note_path = analysis_dir / "weekly_note.md"
        self.meta_path = analysis_dir / "weekly_note.json"

    def save(self, result: WeeklyNoteResult) -> tuple[Path, Path]:
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self.note_path.write_text(result.content + "\n", encoding="utf-8")
        self.meta_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return self.note_path, self.meta_path

    def load_note_text(self) -> str | None:
        if not self.note_path.exists():
            return None
        return self.note_path.read_text(encoding="utf-8").strip()

    def load_result(self) -> WeeklyNoteResult | None:
        if not self.meta_path.exists():
            return None
        return WeeklyNoteResult.model_validate_json(
            self.meta_path.read_text(encoding="utf-8")
        )
