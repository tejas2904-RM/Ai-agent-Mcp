"""Sync analysis artifacts into the API data directory."""

from __future__ import annotations

import shutil
from pathlib import Path

import httpx

from groww_pulse.config import Settings
from groww_pulse.phase9.models import SyncResponse
from groww_pulse.phase9.repository import ArtifactRepository


def sync_artifacts(
    source_dir: Path | None = None,
    target_dir: Path | None = None,
) -> SyncResponse:
    settings = Settings()
    source = source_dir or settings.analysis_data_dir
    target = target_dir or settings.resolved_api_data_dir()
    target.mkdir(parents=True, exist_ok=True)

    synced: list[str] = []
    for name in ArtifactRepository.ARTIFACT_NAMES:
        src = source / name
        dst = target / name
        if not src.exists():
            continue
        if src.resolve() == dst.resolve():
            synced.append(name)
            continue
        shutil.copy2(src, dst)
        synced.append(name)

    return SyncResponse(status="success", files_synced=synced)


def push_artifacts_to_remote(
    *,
    base_url: str,
    source_dir: Path | None = None,
    api_key: str | None = None,
    timeout_seconds: float = 60.0,
) -> SyncResponse:
    settings = Settings()
    source = source_dir or settings.analysis_data_dir
    key = api_key or settings.api_key
    if not key:
        raise ValueError("API_KEY is required to push artifacts to the remote API")

    url = base_url.rstrip("/") + "/api/v1/admin/sync"
    files = []
    open_handles = []
    try:
        for name in ArtifactRepository.ARTIFACT_NAMES:
            path = source / name
            if not path.exists():
                continue
            handle = path.open("rb")
            open_handles.append(handle)
            content_type = "text/markdown" if name.endswith(".md") else "application/json"
            files.append(("files", (name, handle, content_type)))

        response = httpx.post(
            url,
            headers={"X-API-Key": key},
            files=files,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        return SyncResponse.model_validate(response.json())
    finally:
        for handle in open_handles:
            handle.close()
