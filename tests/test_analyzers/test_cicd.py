from __future__ import annotations

"""Tests for CICDAnalyzer."""
import json
from pathlib import Path

import yaml

from product_builders.analyzers.cicd import CICDAnalyzer


def test_detects_github_actions(tmp_path: Path) -> None:
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    workflow = {
        "name": "CI",
        "on": ["push"],
        "jobs": {
            "build": {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"run": "npm test"},
                ],
            }
        },
    }
    (wf_dir / "ci.yml").write_text(yaml.dump(workflow))
    analyzer = CICDAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.platform == "github-actions"


def test_detects_gitlab_ci(tmp_path: Path) -> None:
    (tmp_path / ".gitlab-ci.yml").write_text("stages:\n  - test\n")
    analyzer = CICDAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.platform == "gitlab-ci"


def test_detects_jenkins(tmp_path: Path) -> None:
    (tmp_path / "Jenkinsfile").write_text("pipeline {\n  agent any\n  stages {}\n}\n")
    analyzer = CICDAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.platform == "jenkins"


def test_detects_build_steps(tmp_path: Path) -> None:
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    workflow = {
        "name": "CI",
        "on": ["push"],
        "jobs": {
            "test": {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"run": "npm test"},
                ],
            }
        },
    }
    (wf_dir / "ci.yml").write_text(yaml.dump(workflow))
    analyzer = CICDAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert "npm test" in result.build_steps


def test_detects_docker_deployment(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM node:18\nCOPY . .\nRUN npm install\n")
    analyzer = CICDAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert "docker" in result.deployment_targets


def test_detects_vercel_deployment(tmp_path: Path) -> None:
    (tmp_path / "vercel.json").write_text(json.dumps({"version": 2}))
    analyzer = CICDAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert "vercel" in result.deployment_targets


def test_empty_repo_no_cicd(tmp_path: Path) -> None:
    analyzer = CICDAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.platform is None
    assert any("no ci/cd pipeline" in ap.lower() for ap in result.anti_patterns)


def test_anti_pattern_no_caching(tmp_path: Path) -> None:
    """CI pipeline with single-file config but no caching keyword, should trigger anti-pattern.

    Uses GitLab CI because its config_path points to a single file, allowing the
    read_file-based caching check to work (GitHub Actions config_path is a directory).
    """
    (tmp_path / ".gitlab-ci.yml").write_text(
        "stages:\n  - test\n\ntest_job:\n  stage: test\n  script:\n    - npm test\n"
    )
    analyzer = CICDAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.platform == "gitlab-ci"
    assert any("no caching" in ap.lower() for ap in result.anti_patterns)
