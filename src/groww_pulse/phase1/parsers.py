"""Parse App Store and Play Store review exports (CSV/JSON)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterator

from groww_pulse.phase1.models import ReviewSource, SkippedRow

# Common column aliases per store (public export formats vary).
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "rating": (
        "rating",
        "star rating",
        "stars",
        "score",
        "star_rating",
        "Star Rating",
        "Rating",
    ),
    "title": (
        "title",
        "review title",
        "review_title",
        "Review Title",
        "Title",
        "headline",
    ),
    "text": (
        "text",
        "review",
        "review text",
        "review_text",
        "body",
        "content",
        "Review",
        "Review Text",
        "review body",
    ),
    "date": (
        "date",
        "review date",
        "review_date",
        "created",
        "created_at",
        "timestamp",
        "Review Submit Date and Time",
        "Date",
        "Review Date",
    ),
}


def _normalize_header(name: str) -> str:
    return name.strip().lower().replace("_", " ")


def _build_column_map(fieldnames: list[str]) -> dict[str, str]:
    """Map logical fields to actual CSV/JSON keys."""
    normalized = {_normalize_header(name): name for name in fieldnames}
    mapping: dict[str, str] = {}
    for logical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = _normalize_header(alias)
            if key in normalized:
                mapping[logical] = normalized[key]
                break
    return mapping


def _extract_row(
    raw: dict[str, Any],
    column_map: dict[str, str],
    source: ReviewSource,
    row_number: int,
) -> tuple[dict[str, str] | None, SkippedRow | None]:
    missing = [field for field in ("rating", "title", "text", "date") if field not in column_map]
    if missing:
        return None, SkippedRow(
            source=source,
            row_number=row_number,
            reason=f"Missing columns for fields: {', '.join(missing)}",
        )

    extracted = {
        field: str(raw.get(column_map[field], "") or "").strip()
        for field in ("rating", "title", "text", "date")
    }

    if not any(extracted.values()):
        return None, SkippedRow(
            source=source,
            row_number=row_number,
            reason="Empty row",
        )

    if not extracted["text"]:
        return None, SkippedRow(
            source=source,
            row_number=row_number,
            reason="Missing review text",
            raw_preview=extracted["title"][:80] or None,
        )

    if not extracted["date"]:
        return None, SkippedRow(
            source=source,
            row_number=row_number,
            reason="Missing date",
            raw_preview=extracted["text"][:80],
        )

    if not extracted["rating"]:
        return None, SkippedRow(
            source=source,
            row_number=row_number,
            reason="Missing rating",
            raw_preview=extracted["text"][:80],
        )

    if not extracted["title"]:
        extracted["title"] = "(No title)"

    return extracted, None


def _iter_csv_rows(path: Path) -> tuple[dict[str, str], list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{path.name}: CSV has no header row")
        fieldnames = list(reader.fieldnames)
        column_map = _build_column_map(fieldnames)
        rows = list(reader)
    return column_map, rows


def _iter_json_rows(path: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path.name}: JSON root must be a list")
    if not payload:
        return {}, []
    if not isinstance(payload[0], dict):
        raise ValueError(f"{path.name}: JSON items must be objects")
    fieldnames = list(payload[0].keys())
    column_map = _build_column_map(fieldnames)
    return column_map, payload


def parse_export_file(
    path: Path,
    source: ReviewSource,
) -> tuple[list[dict[str, str]], list[SkippedRow]]:
    """Parse a single export file into raw extracted rows."""
    suffix = path.suffix.lower()
    skipped: list[SkippedRow] = []
    extracted_rows: list[dict[str, str]] = []

    if suffix == ".csv":
        column_map, rows = _iter_csv_rows(path)
    elif suffix == ".json":
        column_map, rows = _iter_json_rows(path)
    else:
        raise ValueError(f"Unsupported format: {suffix}")

    if not column_map:
        raise ValueError(f"{path.name}: no recognizable review columns")

    for index, raw in enumerate(rows, start=2 if suffix == ".csv" else 1):
        extracted, skip = _extract_row(raw, column_map, source, index)
        if skip:
            skipped.append(skip)
            continue
        extracted_rows.append(extracted)

    return extracted_rows, skipped
