"""Uvicorn entry point for the Phase 9 API."""

from __future__ import annotations

import sys

import uvicorn

from groww_pulse.config import Settings


def main() -> None:
    settings = Settings()
    uvicorn.run(
        "groww_pulse.phase9.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    sys.exit(main())
