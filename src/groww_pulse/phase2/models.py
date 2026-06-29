"""Phase 2 PII scrubbing models and reports."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from groww_pulse.phase1.models import NormalizedReview


class PiiCategory(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    USERNAME = "username"
    ID = "id"


class PiiMatch(BaseModel):
    category: PiiCategory
    value: str
    field: str
    review_index: int | None = None


class CategoryCounts(BaseModel):
    email: int = 0
    phone: int = 0
    username: int = 0
    id: int = 0

    def increment(self, category: PiiCategory, count: int = 1) -> None:
        current = getattr(self, category.value)
        setattr(self, category.value, current + count)

    @property
    def total(self) -> int:
        return self.email + self.phone + self.username + self.id

    def add(self, other: CategoryCounts) -> None:
        for category in PiiCategory:
            self.increment(category, getattr(other, category.value))


class ScrubReport(BaseModel):
    input_path: str
    output_path: str
    report_path: str
    input_count: int = 0
    output_count: int = 0
    reviews_modified: int = 0
    removed_counts: CategoryCounts = Field(default_factory=CategoryCounts)
    verification_passed: bool = False
    verification_remaining: CategoryCounts = Field(default_factory=CategoryCounts)
    scrubbed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScrubbedDataset(BaseModel):
    version: int = 2
    scrubbed: bool = True
    count: int = 0
    reviews: list[NormalizedReview] = Field(default_factory=list)
