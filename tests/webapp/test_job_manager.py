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
    assert job.id


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


def test_build_cli_args_analyze():
    mgr = JobManager()
    job = mgr.create_job("analyze", {"repo_path": "/tmp/repo", "name": "test", "heuristic_only": True})
    args = mgr.build_cli_args(job)
    assert "analyze" in args
    assert "/tmp/repo" in args
    assert "--name" in args
    assert "--heuristic-only" in args


def test_build_cli_args_generate():
    mgr = JobManager()
    job = mgr.create_job("generate", {"name": "test", "profile": "engineer", "validate": True})
    args = mgr.build_cli_args(job)
    assert "generate" in args
    assert "--profile" in args
    assert "engineer" in args
    assert "--validate" in args


def test_build_cli_args_check_drift():
    mgr = JobManager()
    job = mgr.create_job("check-drift", {"name": "test", "repo_path": "/tmp/repo", "full": True})
    args = mgr.build_cli_args(job)
    assert "check-drift" in args
    assert "--repo" in args
    assert "--full" in args


def test_build_cli_args_feedback():
    mgr = JobManager()
    job = mgr.create_job("feedback", {"name": "test", "rule": "db", "issue": "wrong"})
    args = mgr.build_cli_args(job)
    assert "feedback" in args
    assert "--rule" in args
    assert "--issue" in args
