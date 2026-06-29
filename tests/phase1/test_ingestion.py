"""Phase 1 ingestion and normalization tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from groww_pulse.phase1.filters import parse_date, parse_rating, remove_duplicates
from groww_pulse.phase1.models import NormalizedReview, ReviewSource
from groww_pulse.phase1.parsers import parse_export_file
from groww_pulse.phase1.pipeline import ingest_reviews
from groww_pulse.phase1.store import ReviewStore

FIXTURES = Path(__file__).parent / "fixtures"
REFERENCE = date(2026, 6, 27)


def test_parse_play_store_alt_columns() -> None:
    rows, skipped = parse_export_file(
        FIXTURES / "play_store_alt_columns.csv",
        ReviewSource.PLAY_STORE,
    )
    assert len(rows) == 5
    assert len(skipped) == 1
    assert skipped[0].reason == "Missing rating"
    assert rows[2]["title"] == "(No title)"


def test_parse_app_store_json_alt_fields() -> None:
    rows, skipped = parse_export_file(
        FIXTURES / "app_store_alt.json",
        ReviewSource.APP_STORE,
    )
    assert len(rows) == 2
    assert len(skipped) == 0


def test_recency_window_filters_old_reviews(tmp_path: Path) -> None:
    output = tmp_path / "reviews.json"
    reviews, report = ingest_reviews(
        input_dir=FIXTURES,
        output_path=output,
        recency_weeks=10,
        reference_date=REFERENCE,
        inputs={ReviewSource.APP_STORE: FIXTURES / "mixed_window.csv"},
    )
    assert len(reviews) == 1
    assert report.outside_window_removed == 1
    assert reviews[0].title == "Recent review"


def test_deduplication() -> None:
    base = NormalizedReview(
        source=ReviewSource.PLAY_STORE,
        rating=5,
        title="Dup",
        text="Same text",
        date=date(2026, 6, 10),
    )
    unique, removed = remove_duplicates([base, base.model_copy()])
    assert len(unique) == 1
    assert removed == 1


def test_rating_and_date_parsing() -> None:
    assert parse_rating("4 stars") == 4
    assert parse_rating("invalid") is None
    assert parse_date("2026-06-01") == date(2026, 6, 1)
    assert parse_date("Jun 01, 2026") == date(2026, 6, 1)


def test_end_to_end_sample_exports(tmp_path: Path, project_root: Path) -> None:
    output = tmp_path / "groww_reviews.json"
    reviews, report = ingest_reviews(
        input_dir=project_root / "data" / "sample",
        output_path=output,
        recency_weeks=12,
        reference_date=REFERENCE,
    )
    assert report.normalized_count == len(reviews)
    assert report.normalized_count >= 18
    assert all(r.source in (ReviewSource.APP_STORE, ReviewSource.PLAY_STORE) for r in reviews)

    store = ReviewStore(output)
    reloaded = store.load()
    assert len(reloaded) == len(reviews)


def test_malformed_rows_do_not_crash_pipeline(tmp_path: Path) -> None:
    output = tmp_path / "out.json"
    _, report = ingest_reviews(
        input_dir=FIXTURES,
        output_path=output,
        reference_date=REFERENCE,
        inputs={ReviewSource.PLAY_STORE: FIXTURES / "play_store_alt_columns.csv"},
    )
    assert report.skip_count >= 1
    assert report.normalized_count >= 1
