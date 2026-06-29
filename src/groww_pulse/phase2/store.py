"""Persist PII-scrubbed reviews and verification report."""

from __future__ import annotations

import json
from pathlib import Path

from groww_pulse.phase1.models import NormalizedReview
from groww_pulse.phase2.models import ScrubReport, ScrubbedDataset


class ScrubbedReviewStore:
    """JSON store for Phase 2 PII-safe reviews."""

    def __init__(self, reviews_path: Path, report_path: Path) -> None:
        self.reviews_path = reviews_path
        self.report_path = report_path

    def save(
        self,
        reviews: list[NormalizedReview],
        report: ScrubReport,
    ) -> tuple[Path, Path]:
        self.reviews_path.parent.mkdir(parents=True, exist_ok=True)

        dataset = ScrubbedDataset(count=len(reviews), reviews=reviews)
        self.reviews_path.write_text(
            dataset.model_dump_json(indent=2),
            encoding="utf-8",
        )
        self.report_path.write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return self.reviews_path, self.report_path

    def load_reviews(self) -> list[NormalizedReview]:
        if not self.reviews_path.exists():
            return []
        dataset = ScrubbedDataset.model_validate_json(
            self.reviews_path.read_text(encoding="utf-8")
        )
        return dataset.reviews

    def load_report(self) -> ScrubReport | None:
        if not self.report_path.exists():
            return None
        return ScrubReport.model_validate_json(
            self.report_path.read_text(encoding="utf-8")
        )
