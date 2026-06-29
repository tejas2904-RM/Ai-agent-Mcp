"""Load and validate sample Groww review export files."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from groww_pulse.config import Settings

REQUIRED_FIELDS = {"rating", "title", "text", "date"}


@dataclass
class SampleLoadResult:
    path: Path
    source: str
    record_count: int
    ok: bool
    error: str | None = None


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")
        missing = REQUIRED_FIELDS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")
        return [dict(row) for row in reader]


def _load_json(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("JSON root must be a list of review objects")
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Item {index} is not an object")
        missing = REQUIRED_FIELDS - set(item.keys())
        if missing:
            raise ValueError(f"Item {index} missing fields: {sorted(missing)}")
    return payload


def load_sample_file(path: Path, source: str) -> SampleLoadResult:
    try:
        if path.suffix.lower() == ".csv":
            records = _load_csv(path)
        elif path.suffix.lower() == ".json":
            records = _load_json(path)
        else:
            raise ValueError(f"Unsupported format: {path.suffix}")

        return SampleLoadResult(
            path=path,
            source=source,
            record_count=len(records),
            ok=True,
        )
    except Exception as exc:  # noqa: BLE001
        return SampleLoadResult(
            path=path,
            source=source,
            record_count=0,
            ok=False,
            error=str(exc),
        )


def load_all_samples(sample_dir: Path | None = None) -> list[SampleLoadResult]:
    settings = Settings()
    directory = sample_dir or settings.sample_data_dir
    results: list[SampleLoadResult] = []

    expected = [
        (directory / "groww_app_store_reviews.csv", "app_store"),
        (directory / "groww_play_store_reviews.csv", "play_store"),
    ]

    for path, source in expected:
        if not path.exists():
            results.append(
                SampleLoadResult(
                    path=path,
                    source=source,
                    record_count=0,
                    ok=False,
                    error="File not found",
                )
            )
            continue
        results.append(load_sample_file(path, source))

    return results
