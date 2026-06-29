"""Fetch public Groww reviews from App Store RSS and Google Play (no login)."""

from __future__ import annotations

import csv
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from groww_pulse.config import Settings

GROWW_APP_STORE_ID = "1404871703"
GROWW_PLAY_PACKAGE = "com.nextbillion.groww"
APP_STORE_COUNTRY = "in"
PLAY_STORE_COUNTRY = "in"

CSV_FIELDS = ("rating", "title", "text", "date")


@dataclass
class FetchReport:
    app_store_fetched: int = 0
    app_store_saved: int = 0
    play_store_fetched: int = 0
    play_store_saved: int = 0
    app_store_path: str | None = None
    play_store_path: str | None = None


def _strip_html(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def _parse_apple_updated(raw: str) -> date | None:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _within_cutoff(review_date: date, cutoff: date) -> bool:
    return review_date >= cutoff


def fetch_app_store_reviews(
    app_id: str = GROWW_APP_STORE_ID,
    country: str = APP_STORE_COUNTRY,
    max_pages: int = 10,
    recency_weeks: int = 12,
    reference_date: date | None = None,
) -> list[dict[str, str]]:
    """Fetch reviews from Apple's public Customer Reviews RSS feed (JSON)."""
    end = reference_date or date.today()
    cutoff = end - timedelta(weeks=recency_weeks)
    collected: list[dict[str, str]] = []
    stop = False

    for page in range(1, max_pages + 1):
        url = (
            f"https://itunes.apple.com/{country}/rss/customerreviews/"
            f"id={app_id}/sortBy=mostRecent/page={page}/json"
        )
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = json.load(response)
        except urllib.error.HTTPError:
            break

        entries = payload.get("feed", {}).get("entry", [])
        if not entries:
            break

        # First entry on page 1 is app metadata, not a review.
        start_index = 1 if page == 1 and "im:rating" not in entries[0] else 0

        for entry in entries[start_index:]:
            rating_raw = entry.get("im:rating", {}).get("label")
            title = entry.get("title", {}).get("label", "").strip()
            text = _strip_html(entry.get("content", {}).get("label", ""))
            updated = entry.get("updated", {}).get("label", "")

            if not rating_raw or not text or not updated:
                continue

            review_date = _parse_apple_updated(updated)
            if review_date is None:
                continue

            if review_date < cutoff:
                stop = True
                break

            collected.append(
                {
                    "rating": str(rating_raw),
                    "title": title or "(No title)",
                    "text": text,
                    "date": review_date.isoformat(),
                }
            )

        if stop:
            break

    return collected


def fetch_play_store_reviews(
    package: str = GROWW_PLAY_PACKAGE,
    country: str = PLAY_STORE_COUNTRY,
    recency_weeks: int = 12,
    reference_date: date | None = None,
    batch_size: int = 200,
    max_batches: int = 25,
) -> list[dict[str, str]]:
    """Fetch reviews from public Google Play listing (no login)."""
    try:
        from google_play_scraper import Sort, reviews
    except ImportError as exc:
        raise ImportError(
            "google-play-scraper is required. Install with: pip install google-play-scraper"
        ) from exc

    end = reference_date or date.today()
    cutoff = end - timedelta(weeks=recency_weeks)
    collected: list[dict[str, str]] = []
    token: str | None = None

    for _ in range(max_batches):
        batch, token = reviews(
            package,
            lang="en",
            country=country,
            sort=Sort.NEWEST,
            count=batch_size,
            continuation_token=token,
        )
        if not batch:
            break

        stop = False
        for item in batch:
            review_at = item["at"]
            if isinstance(review_at, datetime):
                review_date = review_at.date()
            else:
                review_date = datetime.fromisoformat(str(review_at)).date()

            if review_date < cutoff:
                stop = True
                break

            content = (item.get("content") or "").strip()
            if not content:
                continue

            collected.append(
                {
                    "rating": str(item["score"]),
                    "title": "(No title)",
                    "text": content,
                    "date": review_date.isoformat(),
                }
            )

        if stop or token is None:
            break

    return collected


def _write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def fetch_and_save_reviews(
    output_dir: Path | None = None,
    recency_weeks: int | None = None,
    reference_date: date | None = None,
) -> FetchReport:
    settings = Settings()
    directory = output_dir or settings.sample_data_dir
    weeks = max(8, min(12, recency_weeks or settings.recency_weeks))

    app_path = directory / "groww_app_store_reviews.csv"
    play_path = directory / "groww_play_store_reviews.csv"

    app_rows = fetch_app_store_reviews(recency_weeks=weeks, reference_date=reference_date)
    play_rows = fetch_play_store_reviews(recency_weeks=weeks, reference_date=reference_date)

    _write_csv(app_rows, app_path)
    _write_csv(play_rows, play_path)

    return FetchReport(
        app_store_fetched=len(app_rows),
        app_store_saved=len(app_rows),
        play_store_fetched=len(play_rows),
        play_store_saved=len(play_rows),
        app_store_path=str(app_path),
        play_store_path=str(play_path),
    )
