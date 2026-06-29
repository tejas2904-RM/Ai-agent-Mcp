"""FastAPI application for Phase 9 — read-only insights API."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from groww_pulse.config import Settings
from groww_pulse.phase9.auth import require_api_key
from groww_pulse.phase9.models import (
    HealthResponse,
    PulsePayload,
    RunSummary,
    SyncResponse,
    WeekSummary,
)
from groww_pulse.phase9.repository import ArtifactRepository
from groww_pulse.phase9.service import (
    PulseNotFoundError,
    RunNotFoundError,
    build_pulse_payload,
    get_pulse_for_week,
    get_run_summary,
    list_runs,
    list_weeks,
)


def create_app(*, data_dir: Path | None = None) -> FastAPI:
    settings = Settings()
    resolved_dir = data_dir or settings.resolved_api_data_dir()
    repo = ArtifactRepository(resolved_dir)

    app = FastAPI(
        title="Groww Review Pulse API",
        version="1.0.0",
        description="Read-only API for PII-safe weekly Groww review pulse insights.",
    )

    origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            data_dir=str(resolved_dir),
            has_latest_pulse=repo.has_latest_pulse(),
        )

    @app.get("/api/v1/pulse/latest", response_model=PulsePayload)
    def pulse_latest() -> PulsePayload:
        try:
            return build_pulse_payload(repo)
        except PulseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @app.get("/api/v1/pulse/weeks", response_model=list[WeekSummary])
    def pulse_weeks() -> list[WeekSummary]:
        return list_weeks(repo)

    @app.get("/api/v1/pulse/weeks/{week_range}", response_model=PulsePayload)
    def pulse_by_week(week_range: str) -> PulsePayload:
        try:
            return get_pulse_for_week(repo, week_range)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @app.get("/api/v1/runs", response_model=list[RunSummary])
    def runs() -> list[RunSummary]:
        return list_runs(repo)

    @app.get("/api/v1/runs/{run_id}", response_model=RunSummary)
    def run_detail(run_id: str) -> RunSummary:
        try:
            return get_run_summary(repo, run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @app.post(
        "/api/v1/admin/sync",
        response_model=SyncResponse,
        dependencies=[Depends(require_api_key)],
    )
    async def admin_sync(files: list[UploadFile] = File(default=[])) -> SyncResponse:
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files uploaded",
            )
        resolved_dir.mkdir(parents=True, exist_ok=True)
        synced: list[str] = []
        allowed = set(ArtifactRepository.ARTIFACT_NAMES)
        for upload in files:
            if not upload.filename or upload.filename not in allowed:
                continue
            target = resolved_dir / upload.filename
            target.write_bytes(await upload.read())
            synced.append(upload.filename)
        return SyncResponse(status="success", files_synced=synced)

    return app


app = create_app()
