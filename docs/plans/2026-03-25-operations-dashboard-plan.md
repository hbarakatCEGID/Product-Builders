# Operations Dashboard & Executable API — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add executable API endpoints, WebSocket streaming, an operations dashboard, and contextual action buttons to the Product Builders webapp.

**Architecture:** New `routes_api.py` router with POST endpoints that spawn CLI commands as subprocesses. A `job_manager.py` manages a single-job queue with output buffering. A WebSocket at `/ws/execute` streams stdout/stderr to the browser. The frontend uses htmx for tab/form swapping and ~80 lines of vanilla JS for the WebSocket terminal.

**Tech Stack:** FastAPI (existing), WebSocket (built-in), htmx (CDN), vanilla JS, Jinja2 partials.

**Design doc:** `docs/plans/2026-03-25-operations-dashboard-design.md`

---

### Task 1: Job Manager Module

**Files:**
- Create: `src/product_builders/webapp/job_manager.py`
- Test: `tests/webapp/test_job_manager.py`

**Step 1: Write the failing test**

```python
# tests/webapp/test_job_manager.py
"""Tests for job_manager module."""
from __future__ import annotations

import asyncio

import pytest

from product_builders.webapp.job_manager import Job, JobManager, JobStatus


def test_job_creation():
    mgr = JobManager()
    job = mgr.create_job("analyze", {"repo_path": "/tmp/repo", "name": "test"})
    assert job.command == "analyze"
    assert job.status == JobStatus.QUEUED
    assert job.id  # non-empty string


def test_get_job():
    mgr = JobManager()
    job = mgr.create_job("generate", {"name": "test"})
    found = mgr.get_job(job.id)
    assert found is not None
    assert found.id == job.id


def test_get_job_missing():
    mgr = JobManager()
    assert mgr.get_job("nonexistent") is None


def test_reject_concurrent_job():
    mgr = JobManager()
    job1 = mgr.create_job("analyze", {"repo_path": "/tmp", "name": "a"})
    job1.status = JobStatus.RUNNING
    with pytest.raises(RuntimeError, match="already running"):
        mgr.create_job("generate", {"name": "b"})
```

**Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/webapp/test_job_manager.py -v`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```python
# src/product_builders/webapp/job_manager.py
"""Single-job manager with subprocess execution and output buffering."""
from __future__ import annotations

import asyncio
import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    id: str
    command: str
    args: dict[str, Any]
    status: JobStatus = JobStatus.QUEUED
    output_lines: list[dict[str, str]] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    finished_at: datetime | None = None
    exit_code: int | None = None
    error: str | None = None


# Path for recent paths persistence
_RECENT_PATHS_FILE: Path | None = None


def _recent_paths_file() -> Path:
    global _RECENT_PATHS_FILE
    if _RECENT_PATHS_FILE is None:
        from product_builders.config import Config
        config = Config()
        _RECENT_PATHS_FILE = Path(config.home) / "recent_paths.json"
    return _RECENT_PATHS_FILE


def load_recent_paths() -> list[str]:
    """Load recently used paths from disk."""
    path = _recent_paths_file()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(p) for p in data[:10]]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_recent_path(new_path: str) -> None:
    """Add a path to the recent list (max 10, deduped)."""
    paths = load_recent_paths()
    if new_path in paths:
        paths.remove(new_path)
    paths.insert(0, new_path)
    paths = paths[:10]
    fp = _recent_paths_file()
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(paths), encoding="utf-8")


class JobManager:
    """Manages a single-job execution queue."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create_job(self, command: str, args: dict[str, Any]) -> Job:
        """Create a new job. Raises RuntimeError if one is already running."""
        for j in self._jobs.values():
            if j.status == JobStatus.RUNNING:
                raise RuntimeError("A job is already running. Wait for it to finish.")
        job = Job(id=uuid.uuid4().hex[:12], command=command, args=args)
        self._jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def build_cli_args(self, job: Job) -> list[str]:
        """Build the CLI argument list for subprocess execution."""
        args = job.args
        parts: list[str] = [sys.executable, "-m", "product_builders.cli"]

        if job.command == "analyze":
            parts += [
                "analyze", args["repo_path"], "--name", args["name"],
            ]
            if args.get("heuristic_only"):
                parts.append("--heuristic-only")
            if args.get("sub_project"):
                parts += ["--sub-project", args["sub_project"]]

        elif job.command == "generate":
            parts += ["generate", "--name", args["name"]]
            if args.get("profile"):
                parts += ["--profile", args["profile"]]
            if args.get("validate"):
                parts.append("--validate")

        elif job.command == "export":
            parts += [
                "export", "--name", args["name"], "--target", args["target"],
            ]
            if args.get("profile"):
                parts += ["--profile", args["profile"]]

        elif job.command == "setup":
            parts += [
                "setup", "--name", args["name"], "--profile", args["profile"],
            ]

        elif job.command == "check-drift":
            parts += [
                "check-drift", "--name", args["name"], "--repo", args["repo_path"],
            ]
            if args.get("full"):
                parts.append("--full")

        elif job.command == "feedback":
            parts += [
                "feedback", "--name", args["name"],
                "--rule", args["rule"], "--issue", args["issue"],
            ]

        else:
            raise ValueError(f"Unknown command: {job.command}")

        return parts

    async def run_job(self, job: Job) -> None:
        """Execute the job as a subprocess, buffering output lines."""
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(tz=timezone.utc)

        cli_args = self.build_cli_args(job)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cli_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            async def _read_stream(
                stream: asyncio.StreamReader, stream_name: str
            ) -> None:
                async for raw_line in stream:
                    line = raw_line.decode("utf-8", errors="replace").rstrip("\n\r")
                    job.output_lines.append({"line": line, "stream": stream_name})

            await asyncio.gather(
                _read_stream(proc.stdout, "stdout"),  # type: ignore[arg-type]
                _read_stream(proc.stderr, "stderr"),  # type: ignore[arg-type]
            )

            await proc.wait()
            job.exit_code = proc.returncode
            job.status = (
                JobStatus.COMPLETED if proc.returncode == 0 else JobStatus.FAILED
            )
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)
        finally:
            job.finished_at = datetime.now(tz=timezone.utc)

        # Save any paths used
        for key in ("repo_path", "target"):
            if key in job.args and job.args[key]:
                save_recent_path(job.args[key])
```

**Step 4: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/webapp/test_job_manager.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
git add src/product_builders/webapp/job_manager.py tests/webapp/test_job_manager.py
git commit -m "feat(webapp): add job manager for single-job subprocess execution"
```

---

### Task 2: API Router with POST Endpoints

**Files:**
- Create: `src/product_builders/webapp/routes_api.py`
- Test: `tests/webapp/test_routes_api.py`

**Step 1: Write the failing test**

```python
# tests/webapp/test_routes_api.py
"""Tests for API endpoints."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from product_builders.webapp.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_post_analyze_missing_fields(client):
    resp = await client.post("/api/analyze", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_generate_missing_fields(client):
    resp = await client.post("/api/generate", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_feedback_missing_fields(client):
    resp = await client.post("/api/feedback", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_recent_paths(client):
    resp = await client.get("/api/recent-paths")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_metrics_missing_product(client):
    resp = await client.get("/api/metrics/nonexistent-product-xyz")
    assert resp.status_code == 200
    assert resp.json() == []
```

**Step 2: Run test to verify it fails**

Run: `py -3.13 -m pytest tests/webapp/test_routes_api.py -v`
Expected: FAIL — routes not found / 404s

**Step 3: Write minimal implementation**

```python
# src/product_builders/webapp/routes_api.py
"""API router — POST endpoints for CLI commands + WebSocket streaming."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from product_builders.webapp.job_manager import (
    JobManager,
    JobStatus,
    load_recent_paths,
)

router = APIRouter(prefix="/api", tags=["operations"])

# Singleton job manager
_manager = JobManager()


def get_manager() -> JobManager:
    return _manager


# --- Request models ---

class AnalyzeRequest(BaseModel):
    repo_path: str
    name: str
    heuristic_only: bool = False
    sub_project: str | None = None


class GenerateRequest(BaseModel):
    name: str
    profile: str | None = None
    validate: bool = False


class ExportRequest(BaseModel):
    name: str
    target: str
    profile: str | None = None


class SetupRequest(BaseModel):
    name: str
    profile: str


class CheckDriftRequest(BaseModel):
    name: str
    repo_path: str
    full: bool = False


class FeedbackRequest(BaseModel):
    name: str
    rule: str
    issue: str


# --- Response model ---

class JobResponse(BaseModel):
    job_id: str
    command: str
    status: str


# --- Helper ---

def _start_job(command: str, args: dict[str, Any]) -> JobResponse:
    mgr = get_manager()
    try:
        job = mgr.create_job(command, args)
    except RuntimeError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=str(e))
    asyncio.get_event_loop().create_task(mgr.run_job(job))
    return JobResponse(job_id=job.id, command=command, status=job.status.value)


# --- POST endpoints ---

@router.post("/analyze", response_model=JobResponse)
def post_analyze(req: AnalyzeRequest) -> JobResponse:
    return _start_job("analyze", req.model_dump())


@router.post("/generate", response_model=JobResponse)
def post_generate(req: GenerateRequest) -> JobResponse:
    return _start_job("generate", req.model_dump())


@router.post("/export", response_model=JobResponse)
def post_export(req: ExportRequest) -> JobResponse:
    return _start_job("export", req.model_dump())


@router.post("/setup", response_model=JobResponse)
def post_setup(req: SetupRequest) -> JobResponse:
    return _start_job("setup", req.model_dump())


@router.post("/check-drift", response_model=JobResponse)
def post_check_drift(req: CheckDriftRequest) -> JobResponse:
    return _start_job("check-drift", req.model_dump())


@router.post("/feedback", response_model=JobResponse)
def post_feedback(req: FeedbackRequest) -> JobResponse:
    return _start_job("feedback", req.model_dump())


# --- GET endpoints ---

@router.get("/recent-paths")
def get_recent_paths() -> list[str]:
    return load_recent_paths()


@router.get("/metrics/{product_name}")
def get_metrics(product_name: str, limit: int = 80) -> list[dict[str, Any]]:
    from product_builders.config import Config
    from product_builders.metrics import read_recent_events
    config = Config()
    try:
        product_dir = config.get_product_dir(product_name)
    except ValueError:
        return []
    return read_recent_events(product_dir, limit=limit)


# --- WebSocket ---

@router.websocket("/ws/execute")
async def ws_execute(websocket: WebSocket, job_id: str = "") -> None:
    await websocket.accept()
    mgr = get_manager()
    job = mgr.get_job(job_id)

    if job is None:
        await websocket.send_json({"type": "error", "message": "Job not found"})
        await websocket.close()
        return

    sent_count = 0
    start = time.monotonic()

    try:
        while True:
            # Send any new output lines
            while sent_count < len(job.output_lines):
                entry = job.output_lines[sent_count]
                await websocket.send_json({
                    "type": "log",
                    "line": entry["line"],
                    "stream": entry["stream"],
                })
                sent_count += 1

            # Check if job is done
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                duration = (
                    (job.finished_at - job.started_at).total_seconds()
                    if job.finished_at and job.started_at
                    else time.monotonic() - start
                )
                await websocket.send_json({
                    "type": "done",
                    "status": job.status.value,
                    "exit_code": job.exit_code,
                    "duration_s": round(duration, 2),
                    "error": job.error,
                })
                break

            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
```

**Step 4: Wire router into app.py**

Modify: `src/product_builders/webapp/app.py:2-14` — add router import and include.

Add after the existing imports (line 11):

```python
from product_builders.webapp.routes_api import router as api_router
```

Add inside `create_app()`, after the static mount (after line 44):

```python
    app.include_router(api_router)
```

**Step 5: Run test to verify it passes**

Run: `py -3.13 -m pytest tests/webapp/test_routes_api.py -v`
Expected: 5 passed

**Step 6: Commit**

```bash
git add src/product_builders/webapp/routes_api.py tests/webapp/test_routes_api.py src/product_builders/webapp/app.py
git commit -m "feat(webapp): add API router with POST endpoints and WebSocket streaming"
```

---

### Task 3: Operations Dashboard Template + htmx

**Files:**
- Modify: `src/product_builders/webapp/templates/base.html` (add nav link + htmx CDN)
- Create: `src/product_builders/webapp/templates/operations.html`
- Create: `src/product_builders/webapp/templates/partials/form_analyze.html`
- Create: `src/product_builders/webapp/templates/partials/form_generate.html`
- Create: `src/product_builders/webapp/templates/partials/form_export.html`
- Create: `src/product_builders/webapp/templates/partials/form_setup.html`
- Create: `src/product_builders/webapp/templates/partials/form_check_drift.html`
- Create: `src/product_builders/webapp/templates/partials/form_feedback.html`
- Modify: `src/product_builders/webapp/app.py` (add operations route + partial routes)

**Step 1: Add htmx and Operations nav link to base.html**

In `src/product_builders/webapp/templates/base.html`, add after the styles.css link (line 10):

```html
  <script src="https://unpkg.com/htmx.org@2.0.4" integrity="sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+" crossorigin="anonymous"></script>
```

Add "Operations" to the nav (after the "Catalog" link, before the "Install CLI" link):

```html
        <a href="/operations">Operations</a>
```

**Step 2: Create operations.html**

```html
<!-- src/product_builders/webapp/templates/operations.html -->
{% extends "base.html" %}
{% block title %}Operations{% endblock %}
{% block content %}
<section class="page-intro">
  <h1 class="page-title">Operations</h1>
  <p class="lede narrow">Run CLI commands directly from the browser. Output streams in real-time.</p>
</section>

<div class="ops-tabs" role="tablist">
  <button class="tab active" hx-get="/partials/form/analyze" hx-target="#form-area" hx-swap="innerHTML" onclick="activateTab(this)">Analyze</button>
  <button class="tab" hx-get="/partials/form/generate" hx-target="#form-area" hx-swap="innerHTML" onclick="activateTab(this)">Generate</button>
  <button class="tab" hx-get="/partials/form/export" hx-target="#form-area" hx-swap="innerHTML" onclick="activateTab(this)">Export</button>
  <button class="tab" hx-get="/partials/form/setup" hx-target="#form-area" hx-swap="innerHTML" onclick="activateTab(this)">Setup</button>
  <button class="tab" hx-get="/partials/form/check-drift" hx-target="#form-area" hx-swap="innerHTML" onclick="activateTab(this)">Check Drift</button>
  <button class="tab" hx-get="/partials/form/feedback" hx-target="#form-area" hx-swap="innerHTML" onclick="activateTab(this)">Feedback</button>
</div>

<div id="form-area" class="ops-form-area">
  {% include "partials/form_analyze.html" %}
</div>

<div id="terminal" class="ops-terminal" style="display:none;">
  <div class="terminal-header">
    <span class="terminal-title">Output</span>
    <span id="terminal-status" class="badge"></span>
  </div>
  <pre id="terminal-output"></pre>
</div>

<script src="{{ url_for('static', path='operations.js') }}"></script>
{% endblock %}
```

**Step 3: Create form partials**

Each partial is a `<form>` that calls `submitCommand(event, 'commandName')` on submit.

```html
<!-- src/product_builders/webapp/templates/partials/form_analyze.html -->
<form onsubmit="submitCommand(event, 'analyze')">
  <div class="form-grid">
    <label for="repo_path">Repository path <span class="req">*</span></label>
    <div class="input-with-dropdown">
      <input type="text" id="repo_path" name="repo_path" required placeholder="/path/to/repo"
             hx-get="/api/recent-paths" hx-trigger="focus" hx-target="#recent-paths-list" hx-swap="innerHTML">
      <datalist id="recent-paths-list"></datalist>
    </div>

    <label for="name">Product name <span class="req">*</span></label>
    <input type="text" id="name" name="name" required placeholder="my-product">

    <label for="heuristic_only">Options</label>
    <div>
      <label class="checkbox"><input type="checkbox" name="heuristic_only"> Heuristic only</label>
    </div>

    <label for="sub_project">Sub-project</label>
    <input type="text" id="sub_project" name="sub_project" placeholder="apps/web (optional)">
  </div>
  <button type="submit" class="btn btn-primary" id="submit-btn">Run Analyze</button>
</form>
```

```html
<!-- src/product_builders/webapp/templates/partials/form_generate.html -->
<form onsubmit="submitCommand(event, 'generate')">
  <div class="form-grid">
    <label for="name">Product name <span class="req">*</span></label>
    <input type="text" id="name" name="name" required placeholder="my-product">

    <label for="profile">Role</label>
    <select id="profile" name="profile">
      <option value="">All roles</option>
      <option value="engineer">Engineer</option>
      <option value="pm">PM</option>
      <option value="designer">Designer</option>
      <option value="qa">QA</option>
      <option value="technical-pm">Technical PM</option>
    </select>

    <label for="validate">Options</label>
    <div>
      <label class="checkbox"><input type="checkbox" name="validate"> Run validation</label>
    </div>
  </div>
  <button type="submit" class="btn btn-primary" id="submit-btn">Run Generate</button>
</form>
```

```html
<!-- src/product_builders/webapp/templates/partials/form_export.html -->
<form onsubmit="submitCommand(event, 'export')">
  <div class="form-grid">
    <label for="name">Product name <span class="req">*</span></label>
    <input type="text" id="name" name="name" required placeholder="my-product">

    <label for="target">Target repo path <span class="req">*</span></label>
    <input type="text" id="target" name="target" required placeholder="/path/to/target/repo">

    <label for="profile">Role</label>
    <select id="profile" name="profile">
      <option value="">All roles</option>
      <option value="engineer">Engineer</option>
      <option value="pm">PM</option>
      <option value="designer">Designer</option>
      <option value="qa">QA</option>
      <option value="technical-pm">Technical PM</option>
    </select>
  </div>
  <button type="submit" class="btn btn-primary" id="submit-btn">Run Export</button>
</form>
```

```html
<!-- src/product_builders/webapp/templates/partials/form_setup.html -->
<form onsubmit="submitCommand(event, 'setup')">
  <div class="form-grid">
    <label for="name">Product name <span class="req">*</span></label>
    <input type="text" id="name" name="name" required placeholder="my-product">

    <label for="profile">Role <span class="req">*</span></label>
    <select id="profile" name="profile" required>
      <option value="">Select role...</option>
      <option value="engineer">Engineer</option>
      <option value="pm">PM</option>
      <option value="designer">Designer</option>
      <option value="qa">QA</option>
      <option value="technical-pm">Technical PM</option>
    </select>
  </div>
  <button type="submit" class="btn btn-primary" id="submit-btn">Run Setup</button>
</form>
```

```html
<!-- src/product_builders/webapp/templates/partials/form_check_drift.html -->
<form onsubmit="submitCommand(event, 'check-drift')">
  <div class="form-grid">
    <label for="name">Product name <span class="req">*</span></label>
    <input type="text" id="name" name="name" required placeholder="my-product">

    <label for="repo_path">Repository path <span class="req">*</span></label>
    <input type="text" id="repo_path" name="repo_path" required placeholder="/path/to/repo">

    <label for="full">Options</label>
    <div>
      <label class="checkbox"><input type="checkbox" name="full"> Full heuristic re-scan</label>
    </div>
  </div>
  <button type="submit" class="btn btn-primary" id="submit-btn">Run Check Drift</button>
</form>
```

```html
<!-- src/product_builders/webapp/templates/partials/form_feedback.html -->
<form onsubmit="submitCommand(event, 'feedback')">
  <div class="form-grid">
    <label for="name">Product name <span class="req">*</span></label>
    <input type="text" id="name" name="name" required placeholder="my-product">

    <label for="rule">Rule name <span class="req">*</span></label>
    <input type="text" id="rule" name="rule" required placeholder="database">

    <label for="issue">Issue description <span class="req">*</span></label>
    <textarea id="issue" name="issue" required rows="3" placeholder="Describe the inaccuracy..."></textarea>
  </div>
  <button type="submit" class="btn btn-primary" id="submit-btn">Submit Feedback</button>
</form>
```

**Step 4: Add operations route and partial routes to app.py**

In `src/product_builders/webapp/app.py`, inside `create_app()`, add after the `health` endpoint (before `return app`):

```python
    # --- Operations dashboard ---

    @app.get("/operations", response_class=HTMLResponse)
    def operations(request: Request, command: str | None = None, name: str | None = None) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "operations.html",
            _template_ctx(
                request,
                title="Operations — Product Builders",
                preselect_command=command,
                preselect_name=name,
            ),
        )

    # Partial form routes for htmx tab swapping
    _form_templates = {
        "analyze": "partials/form_analyze.html",
        "generate": "partials/form_generate.html",
        "export": "partials/form_export.html",
        "setup": "partials/form_setup.html",
        "check-drift": "partials/form_check_drift.html",
        "feedback": "partials/form_feedback.html",
    }

    @app.get("/partials/form/{command}", response_class=HTMLResponse)
    def form_partial(request: Request, command: str) -> HTMLResponse:
        template_name = _form_templates.get(command)
        if not template_name:
            raise HTTPException(status_code=404, detail="Unknown command")
        return templates.TemplateResponse(request, template_name, {"request": request})
```

**Step 5: Verify the app starts**

Run: `py -3.13 -m product_builders.webapp --port 8099 &` then `curl http://127.0.0.1:8099/operations`
Expected: HTML response with operations page

**Step 6: Commit**

```bash
git add src/product_builders/webapp/templates/operations.html src/product_builders/webapp/templates/partials/ src/product_builders/webapp/app.py src/product_builders/webapp/templates/base.html
git commit -m "feat(webapp): add operations dashboard with htmx tab forms"
```

---

### Task 4: Operations JavaScript (WebSocket Terminal)

**Files:**
- Create: `src/product_builders/webapp/static/operations.js`

**Step 1: Write the JS**

```javascript
// src/product_builders/webapp/static/operations.js
// Operations dashboard — WebSocket terminal + form handling

function activateTab(btn) {
  document.querySelectorAll('.ops-tabs .tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
}

function submitCommand(event, command) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const body = {};

  for (const [key, value] of formData.entries()) {
    if (form.querySelector(`[name="${key}"][type="checkbox"]`)) {
      body[key] = form.querySelector(`[name="${key}"]`).checked;
    } else if (value !== '') {
      body[key] = value;
    }
  }

  // Disable submit button
  const submitBtn = form.querySelector('#submit-btn');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Running...';
  }

  // Show terminal
  const terminal = document.getElementById('terminal');
  const output = document.getElementById('terminal-output');
  const status = document.getElementById('terminal-status');
  terminal.style.display = 'block';
  output.textContent = '';
  status.textContent = 'running';
  status.className = 'badge warn';

  fetch(`/api/${command}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
    .then(resp => {
      if (resp.status === 409) {
        throw new Error('A job is already running. Wait for it to finish.');
      }
      if (!resp.ok) {
        return resp.json().then(d => { throw new Error(d.detail || 'Request failed'); });
      }
      return resp.json();
    })
    .then(data => {
      connectWebSocket(data.job_id, submitBtn);
    })
    .catch(err => {
      output.textContent = `Error: ${err.message}\n`;
      status.textContent = 'error';
      status.className = 'badge warn';
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = submitBtn.dataset.originalText || 'Run';
      }
    });
}

function connectWebSocket(jobId, submitBtn) {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${location.host}/api/ws/execute?job_id=${jobId}`);
  const output = document.getElementById('terminal-output');
  const status = document.getElementById('terminal-status');

  ws.onmessage = function (event) {
    const msg = JSON.parse(event.data);

    if (msg.type === 'log') {
      const span = document.createElement('span');
      span.textContent = msg.line + '\n';
      if (msg.stream === 'stderr') {
        span.className = 'stderr';
      }
      output.appendChild(span);
      output.scrollTop = output.scrollHeight;
    } else if (msg.type === 'done') {
      const isOk = msg.status === 'completed';
      status.textContent = isOk ? `completed (${msg.duration_s}s)` : 'failed';
      status.className = isOk ? 'badge ok' : 'badge warn';

      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = submitBtn.dataset.originalText || 'Run';
      }
    } else if (msg.type === 'error') {
      output.textContent += `Error: ${msg.message}\n`;
    }
  };

  ws.onerror = function () {
    status.textContent = 'connection error';
    status.className = 'badge warn';
    if (submitBtn) {
      submitBtn.disabled = false;
    }
  };
}

// Save original button text on load
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('#submit-btn').forEach(btn => {
    btn.dataset.originalText = btn.textContent;
  });

  // Pre-select tab from URL params
  const params = new URLSearchParams(location.search);
  const cmd = params.get('command');
  if (cmd) {
    const tab = document.querySelector(`.tab[hx-get="/partials/form/${cmd}"]`);
    if (tab) tab.click();
  }

  // Pre-fill name from URL params
  const name = params.get('name');
  if (name) {
    setTimeout(() => {
      const nameInput = document.querySelector('#name');
      if (nameInput) nameInput.value = name;
    }, 200);
  }
});
```

**Step 2: Verify by loading operations page in browser**

Run: Start the server and open `http://127.0.0.1:8000/operations`, check that tabs switch and forms render.

**Step 3: Commit**

```bash
git add src/product_builders/webapp/static/operations.js
git commit -m "feat(webapp): add operations.js WebSocket terminal client"
```

---

### Task 5: CSS Styles for Operations Dashboard

**Files:**
- Modify: `src/product_builders/webapp/static/styles.css` (append new styles)

**Step 1: Append operations styles to styles.css**

Add at the end of `src/product_builders/webapp/static/styles.css`:

```css
/* Operations dashboard */
.ops-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 1.25rem;
  border-bottom: 2px solid var(--border);
  padding-bottom: 0.5rem;
}

.tab {
  padding: 0.5rem 1rem;
  border: 1px solid transparent;
  border-radius: 8px 8px 0 0;
  background: transparent;
  color: var(--muted);
  font-family: var(--font-sans);
  font-size: 0.92rem;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}

.tab:hover {
  color: var(--ink);
}

.tab.active {
  color: var(--accent);
  border-color: var(--border);
  border-bottom-color: var(--bg);
  background: var(--bg-card);
}

.ops-form-area {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.form-grid {
  display: grid;
  grid-template-columns: 10rem 1fr;
  gap: 0.75rem 1rem;
  align-items: center;
  margin-bottom: 1.25rem;
}

.form-grid label {
  font-weight: 600;
  font-size: 0.92rem;
  color: var(--ink);
}

.form-grid input[type="text"],
.form-grid select,
.form-grid textarea {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-family: var(--font-sans);
  font-size: 0.95rem;
  background: #fff;
  color: var(--ink);
}

.form-grid input:focus,
.form-grid select:focus,
.form-grid textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(196, 92, 38, 0.12);
}

.form-grid textarea {
  resize: vertical;
}

.req {
  color: var(--accent);
}

.checkbox {
  font-weight: 400;
  font-size: 0.92rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.ops-terminal {
  background: #1e1e1e;
  border: 1px solid #333;
  border-radius: var(--radius);
  overflow: hidden;
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.6rem 1rem;
  background: #2d2d2d;
  border-bottom: 1px solid #333;
}

.terminal-title {
  color: #aaa;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

#terminal-output {
  padding: 1rem;
  margin: 0;
  color: #d4d4d4;
  font-family: ui-monospace, "Cascadia Code", monospace;
  font-size: 0.85rem;
  line-height: 1.5;
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

#terminal-output .stderr {
  color: #f44747;
}

/* Inline terminal (for contextual buttons) */
.inline-terminal {
  background: #1e1e1e;
  border: 1px solid #333;
  border-radius: var(--radius);
  margin-top: 1rem;
  overflow: hidden;
}

.inline-terminal pre {
  padding: 0.75rem 1rem;
  margin: 0;
  color: #d4d4d4;
  font-family: ui-monospace, "Cascadia Code", monospace;
  font-size: 0.82rem;
  line-height: 1.45;
  max-height: 250px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.inline-terminal .stderr {
  color: #f44747;
}

/* Action buttons row on product page */
.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1.25rem;
}

.btn-sm {
  padding: 0.4rem 0.85rem;
  font-size: 0.85rem;
  border-radius: 999px;
}

.refresh-link {
  color: var(--muted);
  text-decoration: none;
  font-size: 0.85rem;
  padding: 0.15rem 0.35rem;
}

.refresh-link:hover {
  color: var(--accent);
}
```

**Step 2: Verify visually**

Run: Open `http://127.0.0.1:8000/operations` and confirm styles render correctly.

**Step 3: Commit**

```bash
git add src/product_builders/webapp/static/styles.css
git commit -m "feat(webapp): add operations dashboard CSS styles"
```

---

### Task 6: Contextual Buttons on Product and Catalog Pages

**Files:**
- Modify: `src/product_builders/webapp/templates/product.html`
- Modify: `src/product_builders/webapp/templates/catalog.html`
- Create: `src/product_builders/webapp/templates/partials/inline_terminal.html`

**Step 1: Create inline terminal partial**

```html
<!-- src/product_builders/webapp/templates/partials/inline_terminal.html -->
<div class="inline-terminal" id="inline-terminal" style="display:none;">
  <pre id="inline-terminal-output"></pre>
</div>
```

**Step 2: Update product.html**

Replace the full content of `src/product_builders/webapp/templates/product.html`:

```html
{% extends "base.html" %}
{% block title %}{{ product.name }}{% endblock %}
{% block content %}
<section class="page-intro">
  <p class="eyebrow">Profile</p>
  <h1 class="page-title">{{ product.name }}</h1>
  {% if product.description %}
  <p class="lede">{{ product.description }}</p>
  {% endif %}
  <dl class="meta-dl">
    <dt>Primary language</dt>
    <dd>{{ product.primary_language or "\u2014" }}</dd>
    <dt>Last analyzed</dt>
    <dd>{{ product.analysis_timestamp or "\u2014" }}</dd>
  </dl>

  <div class="action-row">
    <a href="/operations?command=analyze&name={{ product.name }}" class="btn btn-ghost btn-sm">Re-analyze</a>
    <a href="/operations?command=generate&name={{ product.name }}" class="btn btn-ghost btn-sm">Regenerate Rules</a>
    <a href="/operations?command=check-drift&name={{ product.name }}" class="btn btn-ghost btn-sm">Check Drift</a>
  </div>
</section>

<section class="install-block">
  <h2>Onboarding guides</h2>
  {% if not onboarding_roles %}
  <p class="muted">No <code>docs/onboarding-*.md</code> files yet. Run <code>product-builders generate --name {{ product.name }}</code>.</p>
  {% else %}
  <ul class="doc-link-list">
    {% for role, label in onboarding_roles %}
    <li><a href="/products/{{ product.name }}/onboarding/{{ role }}">{{ label }}</a></li>
    {% endfor %}
  </ul>
  {% endif %}
</section>
{% endblock %}
```

**Step 3: Update catalog.html**

Replace the full content of `src/product_builders/webapp/templates/catalog.html`:

```html
{% extends "base.html" %}
{% block title %}Product catalog{% endblock %}
{% block content %}
<section class="page-intro">
  <h1 class="page-title">Product catalog</h1>
  <p class="lede narrow">
    Profiles found under <code>PB_PROFILES_DIR</code> (default: <code>profiles/</code> relative to the app).
    Each row links to analysis metadata and onboarding guides.
  </p>
  <div class="action-row">
    <a href="/operations?command=analyze" class="btn btn-primary btn-sm">Analyze New Product</a>
  </div>
</section>

{% if not products %}
<p class="muted">No profile directories found. Run <code>product-builders analyze ...</code> first.</p>
{% else %}
<table class="catalog-table">
  <thead>
    <tr>
      <th>Product</th>
      <th>Language</th>
      <th>Last analyzed</th>
      <th>Status</th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    {% for p in products %}
    <tr>
      <td><a href="/products/{{ p.name }}">{{ p.name }}</a></td>
      <td>{{ p.primary_language or "\u2014" }}</td>
      <td class="muted">{{ p.analysis_timestamp or "\u2014" }}</td>
      <td>{% if p.has_analysis %}<span class="badge ok">profile</span>{% else %}<span class="badge warn">no analysis.json</span>{% endif %}</td>
      <td><a href="/operations?command=analyze&name={{ p.name }}" class="refresh-link" title="Re-analyze">&#x27f3;</a></td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endif %}
{% endblock %}
```

**Step 4: Verify visually**

Open `http://127.0.0.1:8000/products` — confirm "Analyze New Product" button and per-row refresh icons.
Open a product detail page — confirm Re-analyze, Regenerate, Check Drift buttons.

**Step 5: Commit**

```bash
git add src/product_builders/webapp/templates/product.html src/product_builders/webapp/templates/catalog.html src/product_builders/webapp/templates/partials/inline_terminal.html
git commit -m "feat(webapp): add contextual action buttons to catalog and product pages"
```

---

### Task 7: Update pyproject.toml Package Data

**Files:**
- Modify: `pyproject.toml:44-50`

**Step 1: Update package-data to include new files**

In `pyproject.toml`, replace the `package-data` section:

```toml
[tool.setuptools.package-data]
product_builders = [
    "webapp/templates/*.html",
    "webapp/templates/docs/*.html",
    "webapp/templates/partials/*.html",
    "webapp/static/*.css",
    "webapp/static/*.js",
    "webapp/content/docs/*.md",
]
```

**Step 2: Reinstall to pick up new package data**

Run: `py -3.13 -m pip install -e ".[webapp]"`

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: include partials templates and JS in package data"
```

---

### Task 8: End-to-End Manual Test

**No files to create — verification only.**

**Step 1:** Start the server: `py -3.13 -m product_builders.webapp --reload`

**Step 2:** Open `http://127.0.0.1:8000/operations`

**Step 3:** Verify:
- Tabs switch forms correctly (htmx)
- Submit an `analyze` command with a real repo path
- Terminal shows real-time output
- After completion, badge shows "completed" with duration
- Navigate to `/products` — "Analyze New Product" button links to operations
- Navigate to a product detail — Re-analyze/Regenerate/Check Drift buttons link to operations

**Step 4:** Open `http://127.0.0.1:8000/api/docs` — verify all new POST endpoints appear in Swagger and can be tested with "Try it out"

**Step 5:** Run all tests: `py -3.13 -m pytest tests/ -v`

**Step 6: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address issues from e2e testing"
```
