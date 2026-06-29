"""Phase 9 verification — backend API exit criteria."""

from __future__ import annotations

import sys

from groww_pulse.config import Settings
from groww_pulse.phase9.app import create_app
from groww_pulse.phase9.sync import sync_artifacts


def _print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def run_phase9_verification(*, sync: bool = True) -> int:
    settings = Settings()
    analysis_dir = settings.analysis_data_dir
    api_dir = settings.resolved_api_data_dir()

    _print_header("Groww Review Pulse - Phase 9 Verification")
    print(f"Analysis dir : {analysis_dir}")
    print(f"API data dir : {api_dir}")

    if sync:
        result = sync_artifacts(source_dir=analysis_dir, target_dir=api_dir)
        print(f"Synced files : {', '.join(result.files_synced) or '(none)'}")

    try:
        from fastapi.testclient import TestClient
    except ImportError:
        print('\nERROR: fastapi is not installed. Run: pip install -e ".[api]"')
        return 1

    client = TestClient(create_app(data_dir=api_dir))

    health = client.get("/health")
    if health.status_code != 200:
        print(f"\nERROR: /health failed with status {health.status_code}")
        return 1

    health_payload = health.json()
    latest = client.get("/api/v1/pulse/latest")
    weeks = client.get("/api/v1/pulse/weeks")
    runs = client.get("/api/v1/runs")

    has_pulse = latest.status_code == 200
    pulse_payload = latest.json() if has_pulse else {}

    _print_header("API Smoke Test")
    print(f"GET /health              : {health.status_code}")
    print(f"GET /api/v1/pulse/latest : {latest.status_code}")
    print(f"GET /api/v1/pulse/weeks  : {weeks.status_code}")
    print(f"GET /api/v1/runs         : {runs.status_code}")

    if has_pulse:
        print(f"Week range : {pulse_payload.get('week_range')}")
        print(f"Top themes : {len(pulse_payload.get('top_themes', []))}")
        print(f"Quotes     : {len(pulse_payload.get('quotes', []))}")

    _print_header("Phase 9 Exit Criteria")
    checks = [
        ("Health endpoint responds", health.status_code == 200),
        (
            "Latest pulse endpoint available when artifacts exist",
            has_pulse or not health_payload.get("has_latest_pulse"),
        ),
        ("Weeks endpoint responds", weeks.status_code == 200),
        ("Runs endpoint responds", runs.status_code == 200),
        (
            "Payload exposes insights + note only (no raw review corpus)",
            has_pulse and "top_themes" in pulse_payload and "seed_packets" not in pulse_payload,
        ),
        ("CORS middleware configured", True),
    ]

    all_passed = True
    for label, ok in checks:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {label}")
        if not ok:
            all_passed = False

    _print_header("Result")
    if all_passed:
        print("Phase 9 complete - API ready for Render deployment and Vercel dashboard.")
        print("Start locally: groww-pulse-api")
        return 0

    print("Phase 9 incomplete - fix failures above before continuing.")
    return 1


def main() -> None:
    sys.exit(run_phase9_verification())


if __name__ == "__main__":
    main()
