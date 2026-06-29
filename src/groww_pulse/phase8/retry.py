"""Retry helpers for transient orchestration failures."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from groww_pulse.mcp.http_client import HttpMCPError

T = TypeVar("T")

DEFAULT_DELAYS = (5.0, 15.0, 30.0)


def is_retryable_error(exc: BaseException) -> bool:
    if isinstance(exc, HttpMCPError):
        return True
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    message = str(exc).lower()
    return any(
        token in message
        for token in ("timeout", "connection", "429", "503", "502", "temporarily")
    )


def retry_call(
    func: Callable[[], T],
    *,
    label: str,
    max_attempts: int = 3,
    delays: tuple[float, ...] = DEFAULT_DELAYS,
    is_retryable: Callable[[BaseException], bool] | None = None,
) -> T:
    retryable = is_retryable or is_retryable_error
    last_error: BaseException | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= max_attempts or not retryable(exc):
                raise
            delay = delays[min(attempt - 1, len(delays) - 1)]
            time.sleep(delay)

    assert last_error is not None
    raise RuntimeError(f"{label} failed after {max_attempts} attempts") from last_error
