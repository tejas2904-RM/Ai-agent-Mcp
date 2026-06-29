"""Phase 4 pipeline — insight selection via Groq Call #2."""

from __future__ import annotations

import time
from pathlib import Path

from groww_pulse.config import DATA_DIR, Settings
from groww_pulse.phase3.groq_client import GroqClient, GroqClientProtocol, estimate_tokens
from groww_pulse.phase3.models import GroqUsageLog
from groww_pulse.phase3.store import AnalysisStore
from groww_pulse.phase4.insight_agent import (
    build_insight_selection_messages,
    normalize_llm_insights,
    select_insights_with_groq,
)
from groww_pulse.phase4.models import (
    ACTION_IDEA_COUNT,
    INSIGHT_MAX_CALL_TOKENS_IN_OUT,
    INSIGHT_MAX_INPUT_TOKENS,
    INSIGHT_SAMPLE_FALLBACKS,
    INSIGHT_SELECTION_MAX_TOKENS,
    InsightSelectionResult,
    TPM_COOLDOWN_SECONDS,
)
from groww_pulse.phase4.selection import (
    build_insight_packets,
    flatten_allowed_samples,
)
from groww_pulse.phase4.store import InsightStore
from groww_pulse.phase4.validators import build_traceable_quote


class InsightSelectionError(RuntimeError):
    """Raised when Phase 4 insight selection fails."""


def _estimate_call2_input_tokens(packets) -> int:
    messages = build_insight_selection_messages(packets)
    return estimate_tokens("\n".join(message["content"] for message in messages))


def _build_packets_within_budget(theme_result):
    packets = None
    samples_per_theme = INSIGHT_SAMPLE_FALLBACKS[0]
    estimated = 0
    for candidate in INSIGHT_SAMPLE_FALLBACKS:
        packets = build_insight_packets(
            theme_result,
            max_samples_per_theme=candidate,
        )
        estimated = _estimate_call2_input_tokens(packets)
        samples_per_theme = candidate
        in_out = estimated + INSIGHT_SELECTION_MAX_TOKENS
        if (
            estimated <= INSIGHT_MAX_INPUT_TOKENS
            and in_out <= INSIGHT_MAX_CALL_TOKENS_IN_OUT
        ):
            break
    if packets is None:
        raise InsightSelectionError("Failed to build insight packets")
    in_out = estimated + INSIGHT_SELECTION_MAX_TOKENS
    if estimated > INSIGHT_MAX_INPUT_TOKENS or in_out > INSIGHT_MAX_CALL_TOKENS_IN_OUT:
        raise InsightSelectionError(
            f"Call #2 token estimate ({estimated} in + {INSIGHT_SELECTION_MAX_TOKENS} out "
            f"= {in_out}) exceeds caps ({INSIGHT_MAX_INPUT_TOKENS} / "
            f"{INSIGHT_MAX_CALL_TOKENS_IN_OUT}) even after reducing samples"
        )
    return packets, samples_per_theme, estimated


def _fallback_insights(
    packets,
    allowed_samples,
    *,
    model: str,
) -> InsightSelectionResult:
    quotes = []
    action_ideas = []
    for packet in packets:
        if not packet.samples:
            continue
        low_star = next(
            (sample for sample in packet.samples if sample.rating <= 2),
            packet.samples[0],
        )
        quote_text = low_star.text[:200].strip()
        quotes.append(
            build_traceable_quote(low_star, packet.theme.name, quote_text)
        )
        action_ideas.append(
            {
                "theme_name": packet.theme.name,
                "idea": (
                    f"Prioritize fixes for {packet.theme.name.lower()} "
                    f"({packet.theme.review_count} reviews, "
                    f"{packet.theme.low_star_pct}% low-star)."
                ),
            }
        )

    payload = {
        "top_themes": [packet.theme.model_dump() for packet in packets],
        "quotes": [quote.model_dump() for quote in quotes[:ACTION_IDEA_COUNT]],
        "action_ideas": action_ideas[:ACTION_IDEA_COUNT],
    }
    return normalize_llm_insights(payload, packets, allowed_samples, model=model)


def run_insight_selection(
    analysis_dir: Path | None = None,
    *,
    groq_client: GroqClientProtocol | None = None,
    use_groq: bool = True,
    tpm_cooldown: bool = True,
) -> tuple[InsightSelectionResult, GroqUsageLog]:
    settings = Settings()
    analysis_path = analysis_dir or (DATA_DIR / "analysis")
    themes_path = analysis_path / "themes.json"
    usage_path = analysis_path / "groq_usage.json"
    metadata_path = analysis_path / "run_metadata.json"

    theme_store = AnalysisStore(themes_path, usage_path, metadata_path)
    theme_result = theme_store.load_themes()
    if theme_result is None:
        raise FileNotFoundError(
            f"Theme analysis not found at {themes_path}. Run Phase 3 first."
        )
    if len(theme_result.themes) < 3:
        raise InsightSelectionError("Phase 3 produced fewer than 3 themes")

    insight_packets, samples_per_theme, estimated_input = _build_packets_within_budget(
        theme_result
    )
    allowed_samples = flatten_allowed_samples(insight_packets)

    usage_log = theme_store.load_usage()
    model = settings.groq_model
    insight_store = InsightStore(analysis_path)

    if use_groq:
        client = groq_client
        if client is None:
            if not settings.groq_api_key:
                raise InsightSelectionError(
                    "GROQ_API_KEY is not set. Configure it in .env for insight selection."
                )
            client = GroqClient(
                api_key=settings.groq_api_key,
                model=model,
                max_input_tokens=INSIGHT_MAX_INPUT_TOKENS,
                max_total_tokens=INSIGHT_MAX_CALL_TOKENS_IN_OUT,
            )
        result, usage_entry = select_insights_with_groq(
            client,
            insight_packets,
            allowed_samples,
            model=model,
        )
        usage_log.entries.append(usage_entry)
        usage_path.write_text(usage_log.model_dump_json(indent=2), encoding="utf-8")
        if tpm_cooldown:
            time.sleep(TPM_COOLDOWN_SECONDS)
    else:
        result = _fallback_insights(
            insight_packets,
            allowed_samples,
            model=model,
        )

    insight_store.save_insights(result)
    return result, usage_log
