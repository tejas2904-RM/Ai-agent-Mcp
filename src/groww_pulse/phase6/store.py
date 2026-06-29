"""Persist Phase 6 Google Docs delivery artifacts."""

from __future__ import annotations

from pathlib import Path

from groww_pulse.phase6.models import DocDeliveryResult


class DocDeliveryStore:
    def __init__(self, analysis_dir: Path) -> None:
        self.analysis_dir = analysis_dir
        self.result_path = analysis_dir / "doc_delivery.json"

    def save(self, result: DocDeliveryResult) -> Path:
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self.result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return self.result_path

    def load(self) -> DocDeliveryResult | None:
        if not self.result_path.exists():
            return None
        return DocDeliveryResult.model_validate_json(
            self.result_path.read_text(encoding="utf-8")
        )
