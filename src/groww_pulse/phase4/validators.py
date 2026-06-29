"""Quote and action validation for Phase 4."""

from __future__ import annotations

from groww_pulse.phase2.verifier import scan_text
from groww_pulse.phase3.models import ReviewSample
from groww_pulse.phase4.models import (
    ACTION_IDEA_COUNT,
    ActionIdea,
    QUOTE_COUNT,
    TOP_THEME_COUNT,
    InsightSelectionResult,
    TraceableQuote,
)


class InsightValidationError(ValueError):
    """Raised when insight selection output fails guardrails."""


def _quote_core(quote_text: str) -> str:
    stripped = quote_text.strip()
    if stripped.endswith("..."):
        return stripped[:-3].rstrip()
    return stripped


def resolve_quote_text(quote_text: str, sample: ReviewSample) -> str | None:
    """Return a verbatim substring from the sample, allowing compacted Groq quotes."""
    core = _quote_core(quote_text)
    if not core:
        return None
    sample_text = sample.text.strip()
    if core in sample_text:
        return core
    if sample_text.startswith(core):
        return core
    return None


def quote_matches_sample(quote_text: str, sample: ReviewSample) -> bool:
    return resolve_quote_text(quote_text, sample) is not None


def find_matching_sample(
    quote_text: str,
    review_id: int | None,
    samples_by_id: dict[int, ReviewSample],
) -> tuple[ReviewSample, str] | None:
    if review_id is not None and review_id in samples_by_id:
        sample = samples_by_id[review_id]
        resolved = resolve_quote_text(quote_text, sample)
        if resolved is not None:
            return sample, resolved

    for sample in samples_by_id.values():
        resolved = resolve_quote_text(quote_text, sample)
        if resolved is not None:
            return sample, resolved
    return None


def quote_is_pii_free(quote_text: str) -> bool:
    findings = scan_text(quote_text, "quote", 0)
    return len(findings) == 0


def validate_insights(
    result: InsightSelectionResult,
    allowed_samples: list[ReviewSample],
) -> None:
    if len(result.top_themes) != TOP_THEME_COUNT:
        raise InsightValidationError(
            f"Expected {TOP_THEME_COUNT} top themes, got {len(result.top_themes)}"
        )
    if len(result.quotes) != QUOTE_COUNT:
        raise InsightValidationError(
            f"Expected {QUOTE_COUNT} quotes, got {len(result.quotes)}"
        )
    if len(result.action_ideas) != ACTION_IDEA_COUNT:
        raise InsightValidationError(
            f"Expected {ACTION_IDEA_COUNT} action ideas, got {len(result.action_ideas)}"
        )

    samples_by_id = {sample.id: sample for sample in allowed_samples}
    allowed_ids = set(samples_by_id)

    for quote in result.quotes:
        if not quote_is_pii_free(quote.text):
            raise InsightValidationError(
                f"Quote for review #{quote.review_id} contains PII"
            )
        matched = find_matching_sample(quote.text, quote.review_id, samples_by_id)
        if matched is None:
            raise InsightValidationError(
                f"Quote is not verbatim from allowed samples: {quote.text[:80]!r}"
            )
        matched_sample, _resolved = matched
        if matched_sample.id not in allowed_ids:
            raise InsightValidationError(
                f"Quote review_id {quote.review_id} is not in allowed sample set"
            )

    theme_names = {theme.name for theme in result.top_themes}
    for action in result.action_ideas:
        if not action.idea.strip():
            raise InsightValidationError("Action idea must not be empty")
        if action.theme_name not in theme_names:
            raise InsightValidationError(
                f"Action idea theme {action.theme_name!r} is not in top 3 themes"
            )


def build_traceable_quote(sample: ReviewSample, theme_name: str, quote_text: str) -> TraceableQuote:
    return TraceableQuote(
        text=quote_text.strip(),
        review_id=sample.id,
        theme_name=theme_name,
        rating=sample.rating,
        source=sample.source.value,
    )
