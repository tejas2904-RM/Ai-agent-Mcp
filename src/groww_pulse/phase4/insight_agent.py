"""Groq insight selection agent (Call #2)."""

from __future__ import annotations

from typing import Any

from groww_pulse.phase3.groq_client import GroqClientProtocol, estimate_tokens
from groww_pulse.phase3.models import ReviewSample
from groww_pulse.phase4.models import (
    ACTION_IDEA_COUNT,
    INSIGHT_SAMPLE_TEXT_CHARS,
    INSIGHT_SELECTION_MAX_TOKENS,
    QUOTE_COUNT,
    ActionIdea,
    InsightSelectionResult,
    ThemeInsightPacket,
    TopThemeInsight,
    TraceableQuote,
)
from groww_pulse.phase4.validators import (
    InsightValidationError,
    build_traceable_quote,
    find_matching_sample,
    validate_insights,
)

SYSTEM_PROMPT = """You are a product insights analyst for Groww (Stocks, Mutual Funds & Gold).
You receive the top 3 ranked review themes with sample reviews.

Select exactly:
- 3 top themes (preserve provided rank order)
- 3 verbatim user quotes (one per theme, copied exactly from the provided samples)
- 3 concrete action ideas (one per theme, specific and actionable)

Rules:
- Return JSON only.
- Never invent or paraphrase quote text.
- Each quote must include the matching review_id from the samples.
- Action ideas must name the theme they address and propose a concrete product fix.
"""


def _compact_sample(sample: ReviewSample) -> dict[str, object]:
    text = sample.text
    if len(text) > INSIGHT_SAMPLE_TEXT_CHARS:
        text = text[: INSIGHT_SAMPLE_TEXT_CHARS - 3].rstrip() + "..."
    title = sample.title
    if len(title) > 60:
        title = title[:57].rstrip() + "..."
    return {
        "id": sample.id,
        "rating": sample.rating,
        "source": sample.source.value,
        "title": title,
        "text": text,
    }


def build_insight_selection_messages(
    packets: list[ThemeInsightPacket],
) -> list[dict[str, str]]:
    import json

    payload = [
        {
            "rank": packet.rank,
            "theme": {
                "name": packet.theme.name,
                "summary": packet.theme.summary,
                "volume_signal": packet.theme.volume_signal,
                "sentiment_signal": packet.theme.sentiment_signal,
                "review_count": packet.theme.review_count,
            },
            "samples": [_compact_sample(sample) for sample in packet.samples],
        }
        for packet in packets
    ]
    user_content = (
        "Top 3 themes with samples:\n"
        f"{json.dumps(payload, separators=(',', ':'))}\n\n"
        "Return JSON with shape:\n"
        '{"top_themes":[{"rank":1,"name":"...","summary":"..."}],'
        f'"quotes":[{{"text":"verbatim","review_id":0,"theme_name":"..."}}] x {QUOTE_COUNT},'
        f'"action_ideas":[{{"theme_name":"...","idea":"..."}}] x {ACTION_IDEA_COUNT}}}'
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def normalize_llm_insights(
    llm_payload: dict[str, Any],
    packets: list[ThemeInsightPacket],
    allowed_samples: list[ReviewSample],
    *,
    model: str,
) -> InsightSelectionResult:
    samples_by_id = {sample.id: sample for sample in allowed_samples}
    packet_by_rank = {packet.rank: packet for packet in packets}

    top_themes: list[TopThemeInsight] = []
    raw_themes = llm_payload.get("top_themes", [])
    if isinstance(raw_themes, list):
        for item in raw_themes:
            if not isinstance(item, dict):
                continue
            rank = int(item.get("rank", len(top_themes) + 1))
            packet = packet_by_rank.get(rank)
            if packet is None:
                continue
            theme = packet.theme.model_copy()
            if item.get("name"):
                theme.name = str(item["name"])
            if item.get("summary"):
                theme.summary = str(item["summary"])
            top_themes.append(theme)

    if len(top_themes) < 3:
        top_themes = [packet.theme for packet in packets]

    quotes: list[TraceableQuote] = []
    raw_quotes = llm_payload.get("quotes", [])
    if isinstance(raw_quotes, list):
        for item in raw_quotes:
            if not isinstance(item, dict):
                continue
            quote_text = str(item.get("text", "")).strip()
            if not quote_text:
                continue
            review_id = item.get("review_id")
            review_id_int = int(review_id) if review_id is not None else None
            theme_name = str(item.get("theme_name") or top_themes[0].name)
            matched = find_matching_sample(quote_text, review_id_int, samples_by_id)
            if matched is None:
                continue
            sample, resolved_text = matched
            quotes.append(build_traceable_quote(sample, theme_name, resolved_text))

    action_ideas: list[ActionIdea] = []
    raw_actions = llm_payload.get("action_ideas", [])
    if isinstance(raw_actions, list):
        for item in raw_actions:
            if not isinstance(item, dict):
                continue
            theme_name = str(item.get("theme_name", "")).strip()
            idea = str(item.get("idea", "")).strip()
            if theme_name and idea:
                action_ideas.append(ActionIdea(theme_name=theme_name, idea=idea))

    result = InsightSelectionResult(
        model=model,
        top_themes=top_themes[:3],
        quotes=quotes[:3],
        action_ideas=action_ideas[:3],
        allowed_sample_ids=sorted(samples_by_id),
    )
    validate_insights(result, allowed_samples)
    return result


def select_insights_with_groq(
    client: GroqClientProtocol,
    packets: list[ThemeInsightPacket],
    allowed_samples: list[ReviewSample],
    *,
    model: str,
) -> tuple[InsightSelectionResult, Any]:
    messages = build_insight_selection_messages(packets)
    prompt_text = "\n".join(message["content"] for message in messages)
    estimated_input = estimate_tokens(prompt_text)

    payload, usage = client.chat_completion(
        messages=messages,
        max_tokens=INSIGHT_SELECTION_MAX_TOKENS,
        call_id="phase4_insight_selection",
        phase=4,
        purpose="insight_selection",
        estimated_input_tokens=estimated_input,
        response_format={"type": "json_object"},
    )

    try:
        result = normalize_llm_insights(
            payload,
            packets,
            allowed_samples,
            model=model,
        )
    except InsightValidationError:
        raise
    except Exception as exc:
        raise InsightValidationError(f"Failed to normalize Groq insights: {exc}") from exc

    return result, usage
