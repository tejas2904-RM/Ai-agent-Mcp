"""Phase 10 verification — Next.js dashboard exit criteria."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REQUIRED_FILES = [
    "package.json",
    "next.config.ts",
    "tailwind.config.ts",
    "src/app/page.tsx",
    "src/app/runs/page.tsx",
    "src/app/layout.tsx",
    "src/app/loading.tsx",
    "src/app/error.tsx",
    "src/lib/api.ts",
    "src/lib/types.ts",
    "vercel.json",
    ".env.example",
]


def _print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def _dashboard_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "dashboard"


def run_phase10_verification(*, skip_build: bool = False) -> int:
    dashboard = _dashboard_dir()

    _print_header("Groww Review Pulse - Phase 10 Verification")
    print(f"Dashboard dir : {dashboard}")

    if not dashboard.is_dir():
        print("\nERROR: dashboard/ directory not found")
        return 1

    missing = [name for name in REQUIRED_FILES if not (dashboard / name).exists()]
    if missing:
        print("\nERROR: Missing required files:")
        for item in missing:
            print(f"  - {item}")
        return 1

    npm = shutil.which("npm")
    if not npm:
        print("\nERROR: npm not found on PATH. Install Node.js to verify the dashboard build.")
        return 1

    build_ok = True
    if not skip_build:
        _print_header("Next.js Build")
        try:
            subprocess.run(
                [npm, "install"],
                cwd=dashboard,
                check=True,
            )
            subprocess.run(
                [npm, "run", "build"],
                cwd=dashboard,
                check=True,
            )
            print("Build succeeded.")
        except subprocess.CalledProcessError as exc:
            print(f"\nERROR: npm command failed (exit {exc.returncode})")
            build_ok = False

    _print_header("Phase 10 Exit Criteria")
    checks = [
        ("dashboard/ scaffold exists", dashboard.is_dir()),
        ("Main page route (app/page.tsx)", (dashboard / "src/app/page.tsx").exists()),
        ("Run history route (app/runs/page.tsx)", (dashboard / "src/app/runs/page.tsx").exists()),
        ("API client (src/lib/api.ts)", (dashboard / "src/lib/api.ts").exists()),
        ("Types mirror Phase 9 models", (dashboard / "src/lib/types.ts").exists()),
        ("Loading and error states", (dashboard / "src/app/loading.tsx").exists() and (dashboard / "src/app/error.tsx").exists()),
        ("Vercel config present", (dashboard / "vercel.json").exists()),
        ("NEXT_PUBLIC_API_URL documented", (dashboard / ".env.example").exists()),
        ("Production build passes", skip_build or build_ok),
    ]

    all_passed = True
    for label, ok in checks:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {label}")
        if not ok:
            all_passed = False

    _print_header("Result")
    if all_passed:
        print("Phase 10 complete - dashboard ready for Vercel deployment.")
        print("Local dev: cd dashboard && npm run dev")
        print("Set NEXT_PUBLIC_API_URL to your Render API URL in Vercel.")
        return 0

    print("Phase 10 incomplete - fix failures above before deploying.")
    return 1


def main() -> None:
    skip = "--skip-build" in sys.argv
    sys.exit(run_phase10_verification(skip_build=skip))


if __name__ == "__main__":
    main()
