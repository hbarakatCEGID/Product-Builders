"""Job manager for webapp subprocess execution.

Manages single-job subprocess execution of CLI commands, tracking status,
output, and recent paths for the operations dashboard.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from product_builders.config import _DEFAULT_HOME

logger = logging.getLogger(__name__)

_PB_HOME = Path(_DEFAULT_HOME)


# ---------------------------------------------------------------------------
# JobStatus enum
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    """Status of a managed job."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Job dataclass
# ---------------------------------------------------------------------------

@dataclass
class Job:
    """Represents a single CLI job managed by the webapp."""
    id: str
    command: str
    args: dict[str, Any]
    status: JobStatus = JobStatus.QUEUED
    output_lines: list[dict[str, str]] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    finished_at: datetime | None = None
    exit_code: int | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Recent paths helpers
# ---------------------------------------------------------------------------

def _recent_paths_file() -> Path:
    return _PB_HOME / "recent_paths.json"


def load_recent_paths() -> list[str]:
    """Read the list of recently-used paths from ``PB_HOME/recent_paths.json``."""
    path = _recent_paths_file()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(p) for p in data]
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load recent_paths.json: %s", exc)
    return []


def save_recent_path(new_path: str) -> None:
    """Persist *new_path* at the front of the recent-paths list (max 10, deduped)."""
    paths = load_recent_paths()
    # Remove duplicates of new_path
    paths = [p for p in paths if p != new_path]
    # Insert at front
    paths.insert(0, new_path)
    # Keep max 10
    paths = paths[:10]
    out = _recent_paths_file()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(paths, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# JobManager
# ---------------------------------------------------------------------------

class JobManager:
    """Manages creation and execution of CLI subprocess jobs.

    Only one job may be RUNNING at a time.
    """

    _MAX_JOBS = 50

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._running_job_id: str | None = None

    # -- public API ---------------------------------------------------------

    def create_job(self, command: str, args: dict[str, Any]) -> Job:
        """Create a new job.  Raises ``RuntimeError`` if a job is already running."""
        if self._running_job_id is not None:
            running = self._jobs.get(self._running_job_id)
            if running and running.status == JobStatus.RUNNING:
                raise RuntimeError(
                    f"A job is already running (id={running.id}, command={running.command})"
                )
            self._running_job_id = None

        # Evict oldest finished jobs when over capacity
        if len(self._jobs) >= self._MAX_JOBS:
            finished = [
                j for j in self._jobs.values()
                if j.status in (JobStatus.COMPLETED, JobStatus.FAILED)
            ]
            finished.sort(key=lambda j: j.started_at)
            for j in finished[: len(self._jobs) - self._MAX_JOBS + 1]:
                del self._jobs[j.id]

        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, command=command, args=dict(args))
        self._jobs[job_id] = job
        self._running_job_id = job_id
        return job

    def get_job(self, job_id: str) -> Job | None:
        """Return the job with *job_id*, or ``None`` if not found."""
        return self._jobs.get(job_id)

    def build_cli_args(self, job: Job) -> list[str]:
        """Build the subprocess command list for a CLI invocation."""
        base = [sys.executable, "-m", "product_builders.cli"]
        args = job.args
        command = job.command

        if command == "analyze":
            parts = base + ["analyze", args["repo_path"], "--name", args["name"]]
            if args.get("heuristic_only"):
                parts.append("--heuristic-only")
            if args.get("sub_project"):
                parts.extend(["--sub-project", args["sub_project"]])
            return parts

        if command == "generate":
            parts = base + ["generate", "--name", args["name"]]
            if args.get("profile"):
                parts.extend(["--profile", args["profile"]])
            if args.get("validate"):
                parts.append("--validate")
            return parts

        if command == "export":
            parts = base + ["export", "--name", args["name"], "--target", args["target"]]
            if args.get("profile"):
                parts.extend(["--profile", args["profile"]])
            return parts

        if command == "setup":
            parts = base + ["setup", "--name", args["name"], "--profile", args["profile"]]
            return parts

        if command == "check-drift":
            parts = base + ["check-drift", "--name", args["name"], "--repo", args["repo_path"]]
            if args.get("full"):
                parts.append("--full")
            return parts

        if command == "feedback":
            parts = base + [
                "feedback",
                "--name", args["name"],
                "--rule", args["rule"],
                "--issue", args["issue"],
            ]
            return parts

        raise ValueError(f"Unknown command: {command}")

    async def run_job(self, job: Job) -> None:
        """Run the job as a subprocess, streaming stdout/stderr into *job.output_lines*."""
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(tz=timezone.utc)

        cmd = self.build_cli_args(job)
        logger.info("Running job %s: %s", job.id, " ".join(cmd))

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            async def _read_stream(
                stream: asyncio.StreamReader | None,
                stream_name: str,
            ) -> None:
                if stream is None:
                    return
                async for raw_line in stream:
                    text = raw_line.decode("utf-8", errors="replace").rstrip("\n\r")
                    job.output_lines.append({"line": text, "stream": stream_name})

            await asyncio.gather(
                _read_stream(proc.stdout, "stdout"),
                _read_stream(proc.stderr, "stderr"),
            )

            await proc.wait()
            job.exit_code = proc.returncode
            job.status = JobStatus.COMPLETED if proc.returncode == 0 else JobStatus.FAILED

        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)
            logger.exception("Job %s failed with exception", job.id)

        finally:
            job.finished_at = datetime.now(tz=timezone.utc)

        # Save any relevant paths to recent paths
        for key in ("repo_path", "target"):
            value = job.args.get(key)
            if value:
                try:
                    save_recent_path(value)
                except OSError as exc:
                    logger.warning("Could not save recent path %r: %s", value, exc)
