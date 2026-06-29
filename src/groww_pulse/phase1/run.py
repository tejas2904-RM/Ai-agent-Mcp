"""Fetch public reviews then run Phase 1 ingestion."""

from __future__ import annotations

import sys

from groww_pulse.phase1.fetch_reviews import fetch_and_save_reviews
from groww_pulse.phase1.verify import run_phase1_verification


def main() -> None:
    print("=" * 60)
    print("Fetching public Groww reviews (App Store RSS + Google Play)")
    print("=" * 60)

    report = fetch_and_save_reviews()
    print(f"App Store : {report.app_store_saved} reviews -> {report.app_store_path}")
    print(f"Play Store: {report.play_store_saved} reviews -> {report.play_store_path}")
    print()

    sys.exit(run_phase1_verification())


if __name__ == "__main__":
    main()
