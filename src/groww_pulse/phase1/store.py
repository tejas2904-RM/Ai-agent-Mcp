"""Persist normalized reviews to local JSON store."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from groww_pulse.phase1.models import NormalizedReview


class ReviewStore:
    """Lightweight JSON-backed store for normalized reviews."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, reviews: list[NormalizedReview]) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "count": len(reviews),
            "reviews": [review.model_dump(mode="json") for review in reviews],
        }
        self.path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return self.path

    def load(self) -> list[NormalizedReview]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return [NormalizedReview.model_validate(item) for item in payload.get("reviews", [])]

    def exists(self) -> bool:
        return self.path.exists()
