"""Deterministic validation for the weekly note."""

from __future__ import annotations

import re

from groww_pulse.phase2.scrubber import (
    AADHAAR_PATTERN,
    EMAIL_PATTERN,
    LONG_NUMERIC_ID_PATTERN,
    PAN_PATTERN,
    PHONE_PATTERN,
    USERNAME_PATTERN,
    UUID_PATTERN,
)
from groww_pulse.phase5.models import (
    MAX_WORD_COUNT,
    SECTION_ACTIONS,
    SECTION_QUOTES,
    SECTION_THEMES,
    NoteValidationResult,
)

NOTE_PII_PATTERNS: tuple[re.Pattern[str], ...] = (
    EMAIL_PATTERN,
    PHONE_PATTERN,
    USERNAME_PATTERN,
    PAN_PATTERN,
    AADHAAR_PATTERN,
    UUID_PATTERN,
    LONG_NUMERIC_ID_PATTERN,
)


class NoteValidationError(ValueError):
    """Raised when the weekly note fails guardrails."""


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", text))


def _section_slice(content: str, heading_needle: str, next_needles: list[str]) -> str:
    lower = content.lower()
    start = lower.find(heading_needle)
    if start < 0:
        return ""
    section = content[start:]
    lower_section = section.lower()
    end_positions = [
        lower_section.find(needle, len(heading_needle))
        for needle in next_needles
        if lower_section.find(needle, len(heading_needle)) >= 0
    ]
    if end_positions:
        section = section[: min(end_positions)]
    return section


def _count_section_items(section: str) -> int:
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    item_lines = [
        line
        for line in lines
        if line.startswith(("-", "*", "•"))
        or re.match(r"^\d+[\).\]]\s+", line)
    ]
    return len(item_lines)


def note_is_pii_free(content: str) -> bool:
    return not any(pattern.search(content) for pattern in NOTE_PII_PATTERNS)


def validate_note(content: str) -> NoteValidationResult:
    errors: list[str] = []
    word_count = count_words(content)
    word_count_ok = word_count <= MAX_WORD_COUNT
    if not word_count_ok:
        errors.append(f"Word count {word_count} exceeds {MAX_WORD_COUNT}")

    lower = content.lower()
    themes_section = _section_slice(
        content,
        SECTION_THEMES,
        [SECTION_QUOTES, SECTION_ACTIONS],
    )
    quotes_section = _section_slice(
        content,
        SECTION_QUOTES,
        [SECTION_ACTIONS],
    )
    actions_section = _section_slice(content, SECTION_ACTIONS, [])

    theme_items = _count_section_items(themes_section)
    quote_items = _count_section_items(quotes_section)
    action_items = _count_section_items(actions_section)

    sections_ok = (
        SECTION_THEMES in lower
        and SECTION_QUOTES in lower
        and SECTION_ACTIONS in lower
        and theme_items >= 3
        and quote_items >= 3
        and action_items >= 3
    )
    if SECTION_THEMES not in lower:
        errors.append("Missing Top 3 Themes section")
    if SECTION_QUOTES not in lower:
        errors.append("Missing User Quotes section")
    if SECTION_ACTIONS not in lower:
        errors.append("Missing Action Ideas section")
    if theme_items < 3:
        errors.append(f"Expected at least 3 theme items, found {theme_items}")
    if quote_items < 3:
        errors.append(f"Expected at least 3 quote items, found {quote_items}")
    if action_items < 3:
        errors.append(f"Expected at least 3 action items, found {action_items}")

    pii_ok = note_is_pii_free(content)
    if not pii_ok:
        errors.append("PII detected in note")

    scannable_ok = "##" in content or bool(
        re.search(r"^#{1,2}\s+", content, flags=re.MULTILINE)
    )
    if not scannable_ok:
        errors.append("Note must use markdown headings for scannability")

    passed = word_count_ok and sections_ok and pii_ok and scannable_ok
    return NoteValidationResult(
        passed=passed,
        word_count=word_count,
        word_count_ok=word_count_ok,
        sections_ok=sections_ok,
        pii_ok=pii_ok,
        scannable_ok=scannable_ok,
        theme_items=theme_items,
        quote_items=quote_items,
        action_items=action_items,
        errors=errors,
    )


def require_valid_note(content: str) -> NoteValidationResult:
    result = validate_note(content)
    if not result.passed:
        raise NoteValidationError("; ".join(result.errors))
    return result
