from __future__ import annotations

"""Tests for git workflow analyzer."""
import json
from pathlib import Path

from product_builders.analyzers.git_workflow import GitWorkflowAnalyzer


def test_detects_github_platform(tmp_path: Path) -> None:
    """.github/ directory should detect github platform."""
    (tmp_path / ".github").mkdir()
    analyzer = GitWorkflowAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.git_platform == "github"


def test_detects_gitlab_platform(tmp_path: Path) -> None:
    """.gitlab-ci.yml should detect gitlab platform."""
    (tmp_path / ".gitlab-ci.yml").write_text("stages:\n  - build\n  - test")
    analyzer = GitWorkflowAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.git_platform == "gitlab"


def test_detects_github_actions_ci(tmp_path: Path) -> None:
    """.github/workflows/ directory should detect CI config path."""
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: CI\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest")
    analyzer = GitWorkflowAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.ci_config_path == ".github/workflows"


def test_detects_pr_template(tmp_path: Path) -> None:
    """pull_request_template.md should be detected."""
    github = tmp_path / ".github"
    github.mkdir()
    (github / "pull_request_template.md").write_text("## Description\n\n## Changes")
    analyzer = GitWorkflowAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.pr_template_path == ".github/pull_request_template.md"


def test_detects_conventional_commits(tmp_path: Path) -> None:
    """commitlint.config.js should detect conventional commit format."""
    (tmp_path / "commitlint.config.js").write_text(
        "module.exports = { extends: ['@commitlint/config-conventional'] };"
    )
    analyzer = GitWorkflowAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.commit_message_format == "conventional"


def test_detects_codeowners(tmp_path: Path) -> None:
    """CODEOWNERS file should be detected."""
    (tmp_path / "CODEOWNERS").write_text("* @org/team")
    analyzer = GitWorkflowAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.codeowners_path == "CODEOWNERS"


def test_detects_changelog(tmp_path: Path) -> None:
    """CHANGELOG.md should be detected."""
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## 1.0.0\n- Initial release")
    analyzer = GitWorkflowAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.changelog_path == "CHANGELOG.md"


def test_detects_semantic_release(tmp_path: Path) -> None:
    """.releaserc config file should detect semantic-release tool."""
    (tmp_path / ".releaserc").write_text('{"branches": ["main"]}')
    analyzer = GitWorkflowAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.release_tool == "semantic-release"


def test_empty_repo(tmp_path: Path) -> None:
    """Empty repo should have no git platform detected."""
    analyzer = GitWorkflowAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.git_platform is None


def test_anti_pattern_no_codeowners(tmp_path: Path) -> None:
    """.github/ exists but no CODEOWNERS should trigger anti-pattern."""
    (tmp_path / ".github").mkdir()
    analyzer = GitWorkflowAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("codeowners" in ap.lower() for ap in result.anti_patterns)
