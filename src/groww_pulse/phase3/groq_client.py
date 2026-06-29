"""Groq API client with token guards and retry backoff."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Protocol

import httpx

from groww_pulse.phase3.models import GroqUsageEntry

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_BACKOFF_SECONDS = (30, 60)
MAX_RETRIES = 2


class GroqError(RuntimeError):
    """Raised when a Groq API call fails."""


class GroqRateLimitError(GroqError):
    """Raised when Groq returns HTTP 429."""


class GroqTokenBudgetError(GroqError):
    """Raised when a call would exceed configured token limits."""


class GroqClientProtocol(Protocol):
    def chat_completion(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int,
        call_id: str,
        phase: int,
        purpose: str,
        estimated_input_tokens: int,
        response_format: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], GroqUsageEntry]: ...

    def chat_completion_text(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int,
        call_id: str,
        phase: int,
        purpose: str,
        estimated_input_tokens: int,
    ) -> tuple[str, GroqUsageEntry]: ...


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def validate_pre_call_budget(
    estimated_input_tokens: int,
    max_output_tokens: int,
    *,
    max_input_tokens: int,
    max_total_tokens: int,
) -> None:
    if estimated_input_tokens > max_input_tokens:
        raise GroqTokenBudgetError(
            f"Estimated input tokens ({estimated_input_tokens}) exceed cap ({max_input_tokens})"
        )
    if estimated_input_tokens + max_output_tokens > max_total_tokens:
        raise GroqTokenBudgetError(
            "Estimated in+out tokens "
            f"({estimated_input_tokens + max_output_tokens}) exceed cap ({max_total_tokens})"
        )


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise GroqError(f"Groq response was not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise GroqError("Groq response JSON must be an object")
    return payload


def strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:markdown|md)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


class GroqClient:
    def __init__(
        self,
        api_key: str,
        *,
        model: str,
        timeout_seconds: float = 60.0,
        max_input_tokens: int = 3_500,
        max_total_tokens: int = 6_000,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_input_tokens = max_input_tokens
        self.max_total_tokens = max_total_tokens

    def _execute_chat(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int,
        call_id: str,
        phase: int,
        purpose: str,
        estimated_input_tokens: int,
        response_format: dict[str, str] | None = None,
    ) -> tuple[str, GroqUsageEntry]:
        validate_pre_call_budget(
            estimated_input_tokens,
            max_tokens,
            max_input_tokens=self.max_input_tokens,
            max_total_tokens=self.max_total_tokens,
        )

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = httpx.post(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    time.sleep(DEFAULT_BACKOFF_SECONDS[min(attempt, 1)])
                    continue
                raise GroqError(f"Groq request failed: {exc}") from exc

            if response.status_code == 429:
                last_error = GroqRateLimitError("Groq rate limit exceeded (HTTP 429)")
                if attempt < MAX_RETRIES:
                    time.sleep(DEFAULT_BACKOFF_SECONDS[min(attempt, 1)])
                    continue
                raise last_error

            if response.status_code >= 400:
                raise GroqError(
                    f"Groq API error {response.status_code}: {response.text[:500]}"
                )

            body = response.json()
            content = body["choices"][0]["message"]["content"]
            usage = body.get("usage", {})
            entry = GroqUsageEntry(
                call_id=call_id,
                phase=phase,
                purpose=purpose,
                model=self.model,
                estimated_input_tokens=estimated_input_tokens,
                prompt_tokens=int(usage.get("prompt_tokens", 0)),
                completion_tokens=int(usage.get("completion_tokens", 0)),
                total_tokens=int(usage.get("total_tokens", 0)),
                max_tokens=max_tokens,
            )
            return content, entry

        raise GroqError(f"Groq request failed after retries: {last_error}")

    def chat_completion(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int,
        call_id: str,
        phase: int,
        purpose: str,
        estimated_input_tokens: int,
        response_format: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], GroqUsageEntry]:
        content, entry = self._execute_chat(
            messages=messages,
            max_tokens=max_tokens,
            call_id=call_id,
            phase=phase,
            purpose=purpose,
            estimated_input_tokens=estimated_input_tokens,
            response_format=response_format,
        )
        return extract_json_object(content), entry

    def chat_completion_text(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int,
        call_id: str,
        phase: int,
        purpose: str,
        estimated_input_tokens: int,
    ) -> tuple[str, GroqUsageEntry]:
        content, entry = self._execute_chat(
            messages=messages,
            max_tokens=max_tokens,
            call_id=call_id,
            phase=phase,
            purpose=purpose,
            estimated_input_tokens=estimated_input_tokens,
        )
        return strip_markdown_fence(content), entry
