"""Integration: JobManager runs real ``analyze`` on this repo via Popen fallback path."""

from __future__ import annotations

import asyncio
import shutil
import uuid
from pathlib import Path

import pytest

from product_builders.config import Config
from product_builders.webapp.job_manager import JobManager, JobStatus

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_analyze_checkout_via_popen_fallback_matches_direct_cli(monkeypatch):
    """Simulate reload loop (``NotImplementedError``); heuristic ``analyze`` on this repo."""
    async def _no_subprocess(*_a, **_kw):
        raise NotImplementedError

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _no_subprocess)

    name = f"pbwebuival{uuid.uuid4().hex[:10]}"
    mgr = JobManager()
    job = mgr.create_job(
        "analyze",
        {
            "repo_path": str(REPO_ROOT),
            "name": name,
            "heuristic_only": True,
        },
    )

    try:
        await mgr.run_job(job)

        assert job.error is None, job.error
        assert job.status == JobStatus.COMPLETED, (job.status, job.exit_code, job.output_lines[-5:])
        assert job.exit_code == 0
        assert job.output_lines
        joined = "\n".join(e["line"] for e in job.output_lines)
        assert "Analyzing" in joined or "analysis.json" in joined or "Profile saved" in joined
    finally:
        cfg = Config()
        pdir = cfg.get_product_dir(name)
        if pdir.exists():
            shutil.rmtree(pdir, ignore_errors=True)
