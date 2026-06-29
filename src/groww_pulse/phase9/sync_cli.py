"""CLI to sync artifacts locally or push to remote Render API."""

from __future__ import annotations

import argparse
import sys

from groww_pulse.config import Settings
from groww_pulse.phase9.sync import push_artifacts_to_remote, sync_artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync analysis artifacts to API data directory")
    parser.add_argument(
        "--remote-url",
        help="Render API base URL to push artifacts via POST /api/v1/admin/sync",
    )
    args = parser.parse_args()
    settings = Settings()

    if args.remote_url:
        try:
            result = push_artifacts_to_remote(base_url=args.remote_url)
        except (ValueError, OSError) as exc:
            print(f"ERROR: {exc}")
            sys.exit(1)
        print(f"Pushed {len(result.files_synced)} file(s) to {args.remote_url}")
        sys.exit(0)

    result = sync_artifacts()
    print(f"Synced {len(result.files_synced)} file(s) to {settings.resolved_api_data_dir()}")
    for name in result.files_synced:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
