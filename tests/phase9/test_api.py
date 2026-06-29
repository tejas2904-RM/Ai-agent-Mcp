"""Phase 9 backend API tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from groww_pulse.phase9.app import create_app
from groww_pulse.phase9.sync import sync_artifacts


@pytest.fixture
def api_dir(project_root: Path, tmp_path: Path) -> Path:
    source = project_root / "data" / "analysis"
    target = tmp_path / "api-data"
    if source.exists():
        sync_artifacts(source_dir=source, target_dir=target)
    return target


def test_health_endpoint(api_dir: Path) -> None:
    client = TestClient(create_app(data_dir=api_dir))
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "groww-pulse-api"


def test_latest_pulse_endpoint(api_dir: Path) -> None:
    client = TestClient(create_app(data_dir=api_dir))
    response = client.get("/api/v1/pulse/latest")
    if not (api_dir / "insights.json").exists():
        pytest.skip("No analysis artifacts in workspace")
    assert response.status_code == 200
    payload = response.json()
    assert "week_range" in payload
    assert "top_themes" in payload
    assert "quotes" in payload
    assert "seed_packets" not in payload


def test_runs_and_weeks_endpoints(api_dir: Path) -> None:
    client = TestClient(create_app(data_dir=api_dir))
    weeks = client.get("/api/v1/pulse/weeks")
    runs = client.get("/api/v1/runs")
    assert weeks.status_code == 200
    assert runs.status_code == 200


def test_admin_sync_requires_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "test-secret")
    api_dir = tmp_path / "api"
    client = TestClient(create_app(data_dir=api_dir))

    denied = client.post("/api/v1/admin/sync")
    assert denied.status_code == 401

    response = client.post(
        "/api/v1/admin/sync",
        headers={"X-API-Key": "test-secret"},
        files=[("files", ("insights.json", b'{"version":1,"model":"t","top_themes":[],"quotes":[],"action_ideas":[]}', "application/json"))],
    )
    assert response.status_code == 200
    assert (api_dir / "insights.json").exists()


def test_sync_artifacts_copies_files(project_root: Path, tmp_path: Path) -> None:
    source = project_root / "data" / "analysis"
    if not source.exists():
        pytest.skip("No analysis artifacts in workspace")
    target = tmp_path / "synced"
    result = sync_artifacts(source_dir=source, target_dir=target)
    assert result.status == "success"
    assert len(result.files_synced) > 0
    assert (target / "insights.json").exists()
