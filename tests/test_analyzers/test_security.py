from __future__ import annotations

"""Tests for security analyzer."""
import json
from pathlib import Path

from product_builders.analyzers.security import SecurityAnalyzer


def test_detects_zod_validation(tmp_path: Path) -> None:
    pkg = {"dependencies": {"zod": "^3.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = SecurityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.input_validation == "zod"


def test_detects_helmet_middleware(tmp_path: Path) -> None:
    pkg = {"dependencies": {"helmet": "^7.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = SecurityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert "helmet" in result.security_middleware


def test_detects_sentry_csp(tmp_path: Path) -> None:
    pkg = {"dependencies": {"helmet": "^7.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = SecurityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.csp_headers is True


def test_detects_snyk_scanner(tmp_path: Path) -> None:
    (tmp_path / ".snyk").write_text("version: v1.0.0")
    analyzer = SecurityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.vulnerability_scanning == "snyk"


def test_detects_dependabot(tmp_path: Path) -> None:
    github = tmp_path / ".github"
    github.mkdir()
    (github / "dependabot.yml").write_text("version: 2\nupdates:\n  - package-ecosystem: npm")
    analyzer = SecurityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.vulnerability_scanning == "dependabot"


def test_detects_env_not_gitignored(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SECRET_KEY=hunter2")
    # Provide a .gitignore that does NOT mention .env
    (tmp_path / ".gitignore").write_text("node_modules/\ndist/\n")
    analyzer = SecurityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("gitignore" in ap.lower() or ".env" in ap.lower() for ap in result.anti_patterns
               if "critical" in ap.lower())


def test_env_gitignored_no_anti_pattern(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SECRET_KEY=hunter2")
    (tmp_path / ".gitignore").write_text("node_modules/\n.env\ndist/\n")
    analyzer = SecurityAnalyzer()
    result = analyzer.analyze(tmp_path)
    # No CRITICAL anti-pattern about .env gitignore
    critical_env = [ap for ap in result.anti_patterns if "critical" in ap.lower() and ".env" in ap.lower()]
    assert len(critical_env) == 0


def test_empty_repo(tmp_path: Path) -> None:
    analyzer = SecurityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.input_validation is None


def test_anti_pattern_no_validation(tmp_path: Path) -> None:
    analyzer = SecurityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("validation" in ap.lower() for ap in result.anti_patterns)


def test_anti_pattern_no_vuln_scanning(tmp_path: Path) -> None:
    analyzer = SecurityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("vulnerability" in ap.lower() or "scanning" in ap.lower() for ap in result.anti_patterns)
