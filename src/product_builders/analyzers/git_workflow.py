"""Git Workflow Analyzer — Dimension 9 (HIGH IMPACT).

Detects Git platform, branch naming strategy, commit message format,
PR templates, merge strategy, and CI config paths.
Platform-aware: GitHub, GitLab, Azure DevOps, Bitbucket.
"""

from __future__ import annotations

import re
from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer
from product_builders.analyzers.deps import GIT_REMOTE_HOST_TO_PLATFORM
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, GitWorkflowResult

PLATFORM_MARKERS: list[tuple[str, str]] = [
    (".github", "github"),
    (".gitlab-ci.yml", "gitlab"),
    (".gitlab", "gitlab"),
    ("azure-pipelines.yml", "azure-devops"),
    ("azure-pipelines", "azure-devops"),
    ("bitbucket-pipelines.yml", "bitbucket"),
]

CI_CONFIG_PATHS: list[tuple[str, str]] = [
    (".github/workflows", "github-actions"),
    (".gitlab-ci.yml", "gitlab-ci"),
    ("azure-pipelines.yml", "azure-pipelines"),
    ("bitbucket-pipelines.yml", "bitbucket-pipelines"),
    ("Jenkinsfile", "jenkins"),
    (".circleci/config.yml", "circleci"),
    (".travis.yml", "travis-ci"),
    ("cloudbuild.yaml", "google-cloud-build"),
    (".drone.yml", "drone"),
]

PR_TEMPLATE_PATHS: list[str] = [
    ".github/pull_request_template.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/PULL_REQUEST_TEMPLATE/default.md",
    "docs/pull_request_template.md",
    ".gitlab/merge_request_templates/default.md",
]

CODEOWNERS_PATHS: list[str] = [
    ".github/CODEOWNERS",
    "CODEOWNERS",
    "docs/CODEOWNERS",
]

CHANGELOG_PATHS: list[str] = [
    "CHANGELOG.md",
    "HISTORY.md",
    "CHANGES.md",
]

RELEASE_TOOL_PATHS: list[tuple[str, str]] = [
    (".releaserc", "semantic-release"),
    ("release.config.js", "semantic-release"),
    (".changeset/config.json", "changesets"),
    ("release-please-config.json", "release-please"),
    (".goreleaser.yml", "goreleaser"),
    ("cliff.toml", "git-cliff"),
]


class GitWorkflowAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Git Workflow Analyzer"

    @property
    def dimension(self) -> str:
        return "git_workflow"

    def analyze(self, repo_path: Path, *, index=None) -> GitWorkflowResult:
        platform = self._detect_platform(repo_path)
        ci_config = self._detect_ci_config(repo_path)
        pr_template = self._detect_pr_template(repo_path)
        commit_format = self._detect_commit_format(repo_path)
        branch_strategy = self._detect_branch_strategy(repo_path)

        codeowners_path = None
        for p in CODEOWNERS_PATHS:
            if (repo_path / p).exists():
                codeowners_path = p
                break

        changelog_path = None
        for p in CHANGELOG_PATHS:
            if (repo_path / p).exists():
                changelog_path = p
                break

        release_tool = None
        for path, tool in RELEASE_TOOL_PATHS:
            if (repo_path / path).exists():
                release_tool = tool
                break

        result = GitWorkflowResult(
            status=AnalysisStatus.SUCCESS,
            git_platform=platform,
            branch_naming_strategy=branch_strategy,
            commit_message_format=commit_format,
            pr_template_path=pr_template,
            ci_config_path=ci_config,
            codeowners_path=codeowners_path,
            changelog_path=changelog_path,
            release_tool=release_tool,
        )

        anti_patterns = []
        if not result.codeowners_path:
            anti_patterns.append("MEDIUM: no CODEOWNERS file — code review responsibility is unclear")
        if not result.changelog_path:
            anti_patterns.append("LOW: no changelog maintained — release notes will lack context")
        if result.commit_message_format is None:
            anti_patterns.append("LOW: no commit message convention enforced")
        result.anti_patterns = anti_patterns

        return result

    def _detect_platform(self, repo_path: Path) -> str | None:
        for marker, platform in PLATFORM_MARKERS:
            if (repo_path / marker).exists():
                return platform

        # Fallback: parse .git/config remote URL to detect platform
        git_config = repo_path / ".git" / "config"
        if git_config.exists():
            content = self.read_file(git_config)
            if content:
                for host, platform in GIT_REMOTE_HOST_TO_PLATFORM.items():
                    if host in content:
                        return platform

        return None

    def _detect_ci_config(self, repo_path: Path) -> str | None:
        for ci_path, _ in CI_CONFIG_PATHS:
            if (repo_path / ci_path).exists():
                return ci_path
        return None

    def _detect_pr_template(self, repo_path: Path) -> str | None:
        for tmpl_path in PR_TEMPLATE_PATHS:
            if (repo_path / tmpl_path).exists():
                return tmpl_path
        return None

    def _detect_commit_format(self, repo_path: Path) -> str | None:
        # Check for commitlint config
        commitlint_files = [
            ".commitlintrc", ".commitlintrc.json", ".commitlintrc.yaml",
            ".commitlintrc.yml", ".commitlintrc.js", ".commitlintrc.cjs",
            "commitlint.config.js", "commitlint.config.cjs", "commitlint.config.ts",
        ]
        for cf in commitlint_files:
            if (repo_path / cf).exists():
                return "conventional"

        # Check package.json for commitlint dependency
        pkg = repo_path / "package.json"
        if pkg.exists():
            data = self.read_json(pkg)
            if data:
                all_deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }
                if "@commitlint/cli" in all_deps or "commitlint" in all_deps:
                    return "conventional"

                # Check for commitizen
                if "commitizen" in all_deps or "cz-conventional-changelog" in all_deps:
                    return "conventional"

                # Check for gitmoji
                if "gitmoji-cli" in all_deps or "gitmoji-changelog" in all_deps:
                    return "gitmoji"

        # Check for .czrc or .cz.json
        for cz_file in [".czrc", ".cz.json"]:
            if (repo_path / cz_file).exists():
                return "conventional"

        return None

    def _detect_branch_strategy(self, repo_path: Path) -> str | None:
        # Check for branch protection in GitHub config
        github_dir = repo_path / ".github"
        if github_dir.is_dir():
            # Check workflow files for branch patterns
            for wf in self.find_files(github_dir, "*.yml", "*.yaml"):
                content = self.read_file(wf)
                if content:
                    if re.search(r"branches:\s*\[.*main.*\]", content):
                        return "main-based"
                    if re.search(r"branches:\s*\[.*master.*\]", content):
                        return "master-based"
                    if re.search(r"branches:\s*\[.*develop.*\]", content):
                        return "gitflow"

        return None


register(GitWorkflowAnalyzer())
