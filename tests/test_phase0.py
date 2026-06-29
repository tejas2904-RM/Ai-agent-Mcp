"""Tests for Phase 0 foundations."""

from pathlib import Path

from groww_pulse.sample_data import load_all_samples


def test_sample_exports_load(project_root: Path) -> None:
    sample_dir = project_root / "data" / "sample"
    results = load_all_samples(sample_dir)
    assert len(results) == 2
    assert all(r.ok for r in results)
    assert all(r.record_count > 0 for r in results)
