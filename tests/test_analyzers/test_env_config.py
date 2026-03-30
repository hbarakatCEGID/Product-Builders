from __future__ import annotations

"""Tests for environment & configuration analyzer."""
import json
from pathlib import Path

from product_builders.analyzers.env_config import EnvConfigAnalyzer


def test_detects_dotenv_approach(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("DATABASE_URL=postgres://localhost/db")
    analyzer = EnvConfigAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert "dotenv" in result.config_approaches


def test_detects_docker(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM node:20-alpine")
    analyzer = EnvConfigAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.has_docker is True


def test_detects_docker_compose(tmp_path: Path) -> None:
    (tmp_path / "docker-compose.yml").write_text("version: '3.8'\nservices:\n  app:\n    build: .")
    analyzer = EnvConfigAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.docker_compose_path == "docker-compose.yml"


def test_detects_feature_flags_launchdarkly(tmp_path: Path) -> None:
    pkg = {"dependencies": {"@launchdarkly/node-server-sdk": "^9.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = EnvConfigAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.feature_flags_system == "launchdarkly"


def test_detects_kubernetes(tmp_path: Path) -> None:
    k8s = tmp_path / "k8s"
    k8s.mkdir()
    (k8s / "deployment.yaml").write_text("apiVersion: apps/v1\nkind: Deployment")
    analyzer = EnvConfigAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.kubernetes_detected is True


def test_detects_secrets_management(tmp_path: Path) -> None:
    pkg = {"dependencies": {"@infisical/sdk": "^2.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = EnvConfigAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.secrets_management == "infisical"


def test_detects_env_files(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SECRET=abc")
    (tmp_path / ".env.example").write_text("SECRET=")
    (tmp_path / ".env.local").write_text("SECRET=local")
    analyzer = EnvConfigAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert ".env" in result.env_files
    assert ".env.example" in result.env_files
    assert ".env.local" in result.env_files


def test_empty_repo(tmp_path: Path) -> None:
    analyzer = EnvConfigAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.has_docker is False


def test_anti_pattern_k8s_no_secrets(tmp_path: Path) -> None:
    k8s = tmp_path / "k8s"
    k8s.mkdir()
    (k8s / "deployment.yaml").write_text("apiVersion: apps/v1\nkind: Deployment")
    analyzer = EnvConfigAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("kubernetes" in ap.lower() and "secrets" in ap.lower() for ap in result.anti_patterns)


def test_anti_pattern_docker_no_config(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM node:20-alpine")
    analyzer = EnvConfigAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("docker" in ap.lower() and "config" in ap.lower() for ap in result.anti_patterns)
