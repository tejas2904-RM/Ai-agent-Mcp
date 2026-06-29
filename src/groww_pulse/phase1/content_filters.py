"""Review text cleaning — emojis, word count, English-only."""

from __future__ import annotations

import re

from langdetect import LangDetectException, detect

# Minimum words required in review body (must be *more than* 6).
MIN_REVIEW_WORDS = 7

# Broad emoji / pictograph ranges (no extra dependency).
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE,
)

# Variation selectors and zero-width joiners often left after emoji removal.
EMOJI_MODIFIER_PATTERN = re.compile(r"[\u200d\ufe0f\u2640-\u2642\u2600-\u26ff]+")


def remove_emojis(text: str) -> str:
    cleaned = EMOJI_PATTERN.sub("", text)
    cleaned = EMOJI_MODIFIER_PATTERN.sub("", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def count_words(text: str) -> int:
    if not text.strip():
        return 0
    return len(re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE))


def review_word_count(title: str, text: str) -> int:
    """Count words in review content (title + body, ignoring placeholder title)."""
    parts: list[str] = []
    if title and title.strip().lower() != "(no title)":
        parts.append(title.strip())
    parts.append(text.strip())
    return count_words(" ".join(parts))


def is_english(text: str) -> bool:
    sample = text.strip()
    if not sample:
        return False
    try:
        return detect(sample) == "en"
    except LangDetectException:
        return False


def clean_review_text(title: str, text: str) -> tuple[str, str]:
    """Strip emojis and normalize whitespace in title and body."""
    clean_title = remove_emojis(title)
    clean_text = remove_emojis(text)
    return clean_title, clean_text
