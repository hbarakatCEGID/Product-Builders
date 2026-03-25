"""API router – POST endpoints for CLI commands, GET for recent paths / metrics, WS for streaming."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from product_builders.config import PROFILES_DIR, validate_product_name
from product_builders.metrics import read_recent_events
from product_builders.webapp.job_manager import JobManager, JobStatus, load_recent_paths

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton job manager
# ---------------------------------------------------------------------------

mgr = JobManager()

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class _NamedRequest(BaseModel):
    """Base for requests that include a product name."""

    name: str

    @field_validator("name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        validate_product_name(v)
        return v


class AnalyzeRequest(_NamedRequest):
    repo_path: str
    heuristic_only: bool = False
    sub_project: str | None = None


class GenerateRequest(_NamedRequest):
    profile: str | None = None
    validate_output: bool = Field(default=False, alias="validate")

    model_config = {"populate_by_name": True}


class ExportRequest(_NamedRequest):
    target: str
    profile: str | None = None


class SetupRequest(_NamedRequest):
    profile: str


class CheckDriftRequest(_NamedRequest):
    repo_path: str
    full: bool = False


class FeedbackRequest(_NamedRequest):
    rule: str
    issue: str


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


class JobResponse(BaseModel):
    job_id: str
    command: str
    status: str


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api")


# -- helper ----------------------------------------------------------------

def _start_job(command: str, args: dict[str, Any]) -> JobResponse | JSONResponse:
    """Create a job and schedule it.  Returns 409 if one is already running."""
    try:
        job = mgr.create_job(command, args)
    except RuntimeError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    asyncio.ensure_future(mgr.run_job(job))
    return JobResponse(job_id=job.id, command=job.command, status=job.status.value)


# -- POST endpoints --------------------------------------------------------

@router.post("/analyze", response_model=None)
async def post_analyze(body: AnalyzeRequest) -> JobResponse | JSONResponse:
    return _start_job("analyze", body.model_dump())


@router.post("/generate", response_model=None)
async def post_generate(body: GenerateRequest) -> JobResponse | JSONResponse:
    return _start_job("generate", body.model_dump(by_alias=True))


@router.post("/export", response_model=None)
async def post_export(body: ExportRequest) -> JobResponse | JSONResponse:
    return _start_job("export", body.model_dump())


@router.post("/setup", response_model=None)
async def post_setup(body: SetupRequest) -> JobResponse | JSONResponse:
    return _start_job("setup", body.model_dump())


@router.post("/check-drift", response_model=None)
async def post_check_drift(body: CheckDriftRequest) -> JobResponse | JSONResponse:
    return _start_job("check-drift", body.model_dump())


@router.post("/feedback", response_model=None)
async def post_feedback(body: FeedbackRequest) -> JobResponse | JSONResponse:
    return _start_job("feedback", body.model_dump())


# -- GET endpoints ---------------------------------------------------------

@router.get("/recent-paths")
async def get_recent_paths() -> list[str]:
    return load_recent_paths()


@router.get("/metrics/{product_name}")
async def get_metrics(product_name: str) -> list[dict[str, Any]]:
    product_dir = PROFILES_DIR / product_name
    return read_recent_events(product_dir)


# -- WebSocket endpoint ----------------------------------------------------

@router.websocket("/ws/execute")
async def ws_execute(websocket: WebSocket, job_id: str = "") -> None:
    await websocket.accept()

    job = mgr.get_job(job_id)
    if job is None:
        await websocket.send_json({"type": "error", "message": "Job not found"})
        await websocket.close()
        return

    sent = 0
    try:
        while True:
            # Send any new output lines
            current_lines = job.output_lines
            if sent < len(current_lines):
                for line_entry in current_lines[sent:]:
                    await websocket.send_json({"type": "log", **line_entry})
                sent = len(current_lines)

            # Check if the job is done
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                # Flush any remaining lines
                if sent < len(job.output_lines):
                    for line_entry in job.output_lines[sent:]:
                        await websocket.send_json({"type": "log", **line_entry})

                duration_s = 0.0
                if job.finished_at and job.started_at:
                    duration_s = round(
                        (job.finished_at - job.started_at).total_seconds(), 1
                    )

                await websocket.send_json(
                    {
                        "type": "done",
                        "status": job.status.value,
                        "exit_code": job.exit_code,
                        "duration_s": duration_s,
                        "error": job.error,
                    }
                )
                await websocket.close()
                return

            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected for job %s", job_id)
