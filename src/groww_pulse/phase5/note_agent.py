"""Groq weekly note generator (Call #3 / optional #4)."""

from __future__ import annotations

from groww_pulse.phase3.groq_client import GroqClientProtocol, estimate_tokens
from groww_pulse.phase4.models import InsightSelectionResult
from groww_pulse.phase5.models import (
    MAX_WORD_COUNT,
    NOTE_GENERATION_MAX_TOKENS,
    NOTE_RETRY_MAX_TOKENS,
    PRODUCT_NAME,
    build_note_title,
)

SYSTEM_PROMPT = f"""You are writing the weekly review pulse for {PRODUCT_NAME} (Stocks, Mutual Funds & Gold).
Produce a scannable markdown note for product and leadership stakeholders.

Rules:
- Use markdown with level-2 headings (##).
- Maximum {MAX_WORD_COUNT} words total.
- Required sections:
  1. A single top-level title line: # {PRODUCT_NAME} Weekly Review Pulse - <week range>
  2. ## Top 3 Themes — exactly 3 bullet items with one-line summary and volume/sentiment signal
  3. ## User Quotes — exactly 3 bullet items using the provided quote text verbatim
  4. ## Action Ideas — exactly 3 bullet items tied to the themes
- No PII. Do not invent quotes.
- Keep language concise and executive-friendly.
"""


def build_note_generation_messages(
    insights: InsightSelectionResult,
    *,
    week_range: str,
    validation_feedback: str | None = None,
) -> list[dict[str, str]]:
    payload = {
        "week_range": week_range,
        "top_themes": [theme.model_dump() for theme in insights.top_themes],
        "quotes": [quote.model_dump() for quote in insights.quotes],
        "action_ideas": [action.model_dump() for action in insights.action_ideas],
    }
    user_parts = [
        f"Week range: {week_range}",
        f"Structured insights JSON:\n{payload}",
        f"Write the weekly pulse markdown (<= {MAX_WORD_COUNT} words).",
    ]
    if validation_feedback:
        user_parts.append(f"Fix these validation issues:\n{validation_feedback}")
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def generate_note_with_groq(
    client: GroqClientProtocol,
    insights: InsightSelectionResult,
    *,
    week_range: str,
    model: str,
    retry: bool = False,
    validation_feedback: str | None = None,
) -> tuple[str, object]:
    messages = build_note_generation_messages(
        insights,
        week_range=week_range,
        validation_feedback=validation_feedback,
    )
    prompt_text = "\n".join(message["content"] for message in messages)
    estimated_input = estimate_tokens(prompt_text)
    max_tokens = NOTE_RETRY_MAX_TOKENS if retry else NOTE_GENERATION_MAX_TOKENS
    call_id = "phase5_note_retry" if retry else "phase5_note_generation"
    purpose = "note_retry" if retry else "note_generation"

    content, usage = client.chat_completion_text(
        messages=messages,
        max_tokens=max_tokens,
        call_id=call_id,
        phase=5,
        purpose=purpose,
        estimated_input_tokens=estimated_input,
    )
    return content.strip(), usage


def render_fallback_note(
    insights: InsightSelectionResult,
    *,
    week_range: str,
) -> str:
    title = build_note_title(week_range)
    lines = [f"# {title}", "", "## Top 3 Themes"]
    for theme in insights.top_themes:
        lines.append(
            f"- **{theme.name}** — {theme.summary} "
            f"({theme.volume_signal} volume, {theme.sentiment_signal} sentiment)."
        )
    lines.extend(["", "## User Quotes"])
    for quote in insights.quotes:
        snippet = quote.text
        if len(snippet) > 120:
            snippet = snippet[:117].rstrip() + "..."
        lines.append(f'- "{snippet}"')
    lines.extend(["", "## Action Ideas"])
    for action in insights.action_ideas:
        lines.append(f"- **{action.theme_name}:** {action.idea}")
    return "\n".join(lines).strip()
