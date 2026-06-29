"""Phase 0 verification — project skeleton, MCP connectivity, sample data."""

from __future__ import annotations

import sys
from pathlib import Path

from groww_pulse.config import Settings, load_mcp_servers
from groww_pulse.mcp.client import discover_all_sync
from groww_pulse.mcp.discovery import ServerValidation, validate_server
from groww_pulse.sample_data import load_all_samples


def _print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def _print_mcp_results(validations: list[ServerValidation]) -> None:
    for result in validations:
        status = "OK" if result.connected else "FAIL"
        print(f"\n[{status}] MCP server: {result.server_name}")
        if result.error:
            print(f"  Error: {result.error}")
            continue

        print(f"  Tools discovered: {len(result.available_tools)}")
        for tool in result.available_tools:
            print(f"    - {tool}")

        print("  Required tools:")
        for check in result.required_checks:
            mark = "OK" if check.satisfied else "MISSING"
            matched = f" (matched: {check.matched_tool})" if check.matched_tool else ""
            print(f"    [{mark}] {check.logical_name}{matched}")


def run_phase0_verification() -> int:
    settings = Settings()
    config_path = settings.resolve_mcp_config_path()

    _print_header("Groww Review Pulse — Phase 0 Verification")
    print(f"Project root : {Path(__file__).resolve().parents[3]}")
    print(f"MCP profile  : {settings.mcp_profile}")
    print(f"MCP config   : {config_path}")

    # 1. Sample data
    _print_header("Sample Groww Review Exports")
    sample_results = load_all_samples()
    samples_ok = True
    for sample in sample_results:
        status = "OK" if sample.ok else "FAIL"
        print(f"[{status}] {sample.source}: {sample.path.name}")
        if sample.ok:
            print(f"       {sample.record_count} records loaded")
        else:
            print(f"       Error: {sample.error}")
            samples_ok = False

    # 2. MCP discovery
    _print_header("MCP Server Connectivity & Tool Discovery")
    servers = load_mcp_servers(config_path)
    discoveries = discover_all_sync(servers)
    validations = [
        validate_server(server, discovery)
        for server, discovery in zip(servers, discoveries, strict=True)
    ]
    _print_mcp_results(validations)

    mcp_ok = all(v.connected for v in validations)
    tools_ok = all(v.all_required_present for v in validations)

    # 3. Summary
    _print_header("Phase 0 Exit Criteria")
    checks = [
        ("Project runs with no errors", True),
        ("Google Docs MCP server connects and lists tools", validations[0].connected if validations else False),
        ("Gmail MCP server connects and lists tools", validations[1].connected if len(validations) > 1 else False),
        ("Required tools confirmed on each server", tools_ok),
        ("Sample Groww review exports load without error", samples_ok),
    ]

    all_passed = True
    for label, passed in checks:
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {label}")
        if not passed:
            all_passed = False

    _print_header("Result")
    if all_passed:
        print("Phase 0 complete — ready for Phase 1.")
        return 0

    print("Phase 0 incomplete — fix failures above before continuing.")
    if settings.mcp_profile == "local":
        print(
            "\nTip: Local profile uses bundled mock MCP servers. "
            "For Google remote MCP, set MCP_PROFILE=remote and configure OAuth."
        )
    return 1


def main() -> None:
    sys.exit(run_phase0_verification())


if __name__ == "__main__":
    main()
