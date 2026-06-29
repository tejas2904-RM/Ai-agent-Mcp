"""Ingestion pipeline — import, normalize, filter, dedupe, persist."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from groww_pulse.config import DATA_DIR, Settings
from groww_pulse.phase1.filters import (
    normalize_row,
    recency_window,
    remove_duplicates,
)
from groww_pulse.phase1.models import (
    IngestionReport,
    NormalizedReview,
    ReviewSource,
    SkippedRow,
)
from groww_pulse.phase1.parsers import parse_export_file
from groww_pulse.phase1.store import ReviewStore

DEFAULT_INPUTS: dict[ReviewSource, str] = {
    ReviewSource.APP_STORE: "groww_app_store_reviews.csv",
    ReviewSource.PLAY_STORE: "groww_play_store_reviews.csv",
}


def _clamp_weeks(weeks: int) -> int:
    return max(8, min(12, weeks))


def ingest_reviews(
    input_dir: Path | None = None,
    output_path: Path | None = None,
    recency_weeks: int | None = None,
    reference_date: date | None = None,
    inputs: dict[ReviewSource, Path] | None = None,
) -> tuple[list[NormalizedReview], IngestionReport]:
    settings = Settings()
    source_dir = input_dir or settings.sample_data_dir
    weeks = _clamp_weeks(recency_weeks or settings.recency_weeks)
    window_start, window_end = recency_window(weeks, reference_date)

    store_path = output_path or (DATA_DIR / "normalized" / "groww_reviews.json")
    report = IngestionReport(
        input_files=[],
        window_weeks=weeks,
        window_start=window_start,
        window_end=window_end,
    )

    normalized: list[NormalizedReview] = []
    file_map = inputs or {
        source: source_dir / filename for source, filename in DEFAULT_INPUTS.items()
    }

    for source, path in file_map.items():
        report.input_files.append(str(path))
        if not path.exists():
            report.skipped.append(
                SkippedRow(
                    source=source,
                    row_number=0,
                    reason=f"Input file not found: {path.name}",
                )
            )
            continue

        raw_rows, parse_skipped = parse_export_file(path, source)
        report.imported_raw += len(raw_rows) + len(parse_skipped)
        report.skipped.extend(parse_skipped)

        for index, raw in enumerate(raw_rows, start=1):
            review, skip, outside = normalize_row(
                raw,
                source,
                row_number=index,
                window_start=window_start,
                window_end=window_end,
            )
            if outside:
                report.outside_window_removed += 1
                continue
            if skip:
                if skip.reason.startswith("Too few words"):
                    report.too_short_removed += 1
                elif skip.reason == "Non-English review":
                    report.non_english_removed += 1
                report.skipped.append(skip)
                continue
            if review:
                normalized.append(review)

    deduped, dup_count = remove_duplicates(normalized)
    report.duplicates_removed = dup_count
    report.normalized_count = len(deduped)

    store = ReviewStore(store_path)
    saved = store.save(deduped)
    report.output_path = str(saved)

    return deduped, report
