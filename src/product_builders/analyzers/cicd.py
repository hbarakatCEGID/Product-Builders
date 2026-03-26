"""CI/CD Analyzer — Dimension 14 (MEDIUM IMPACT).

Detects CI/CD platform, config paths, build steps,
deployment targets, and required checks.
"""

from __future__ import annotations

from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, CICDResult

_CI_PLATFORMS: list[tuple[str, str, str]] = [
    (".github/workflows", "github-actions", ".github/workflows/"),
    (".gitlab-ci.yml", "gitlab-ci", ".gitlab-ci.yml"),
    ("azure-pipelines.yml", "azure-pipelines", "azure-pipelines.yml"),
    ("Jenkinsfile", "jenkins", "Jenkinsfile"),
    ("bitbucket-pipelines.yml", "bitbucket-pipelines", "bitbucket-pipelines.yml"),
    (".circleci/config.yml", "circleci", ".circleci/config.yml"),
    (".travis.yml", "travis-ci", ".travis.yml"),
    ("cloudbuild.yaml", "google-cloud-build", "cloudbuild.yaml"),
    ("cloudbuild.yml", "google-cloud-build", "cloudbuild.yml"),
    ("buildspec.yml", "aws-codebuild", "buildspec.yml"),
    (".drone.yml", "drone", ".drone.yml"),
    (".woodpecker.yml", "woodpecker", ".woodpecker.yml"),
    (".buildkite/pipeline.yml", "buildkite", ".buildkite/pipeline.yml"),
    ("dagger.json", "dagger", "dagger.json"),
    ("appveyor.yml", "appveyor", "appveyor.yml"),
]


class CICDAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "CI/CD Analyzer"

    @property
    def dimension(self) -> str:
        return "cicd"

    def analyze(self, repo_path: Path, *, index=None) -> CICDResult:
        platform, config_path = self._detect_platform(repo_path)
        build_steps = self._detect_build_steps(repo_path, platform, config_path)
        deployment_targets = self._detect_deployment_targets(repo_path)
        required_checks = self._detect_required_checks(repo_path, platform, config_path)

        # Detect caching and matrix builds from workflow files
        caching_detected = False
        matrix_builds = False
        if config_path:
            content = self.read_file(repo_path / config_path)
            if content:
                if "cache" in content.lower():
                    caching_detected = True
                if "matrix" in content.lower() or "strategy:" in content:
                    matrix_builds = True

        result = CICDResult(
            status=AnalysisStatus.SUCCESS,
            platform=platform,
            config_path=config_path,
            build_steps=build_steps,
            deployment_targets=deployment_targets,
            required_checks=required_checks,
            caching_detected=caching_detected,
            matrix_builds=matrix_builds,
        )

        # Anti-pattern detection
        anti_patterns = []

        if result.platform is None:
            anti_patterns.append("HIGH: no CI/CD pipeline detected")

        if result.platform and not result.caching_detected:
            # Check if the workflow file mentions cache
            if result.config_path:
                content = self.read_file(repo_path / result.config_path)
                if content and "cache" not in content.lower():
                    anti_patterns.append("MEDIUM: CI pipeline detected but no caching configured")

        if result.platform and not result.deployment_targets:
            anti_patterns.append("MEDIUM: CI pipeline exists but no deployment targets detected")

        result.anti_patterns = anti_patterns

        return result

    def _detect_platform(self, repo_path: Path) -> tuple[str | None, str | None]:
        for path_check, platform, config in _CI_PLATFORMS:
            full = repo_path / path_check
            if full.exists():
                return platform, config
        return None, None

    def _detect_build_steps(self, repo_path: Path, platform: str | None, config_path: str | None) -> list[str]:
        if not config_path:
            return []

        steps: list[str] = []
        if platform == "github-actions":
            workflows_dir = repo_path / ".github" / "workflows"
            if workflows_dir.is_dir():
                for wf in sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml")):
                    data = self.read_yaml(wf)
                    if not isinstance(data, dict):
                        continue
                    for job_name, job in data.get("jobs", {}).items():
                        if isinstance(job, dict):
                            for step in job.get("steps", []):
                                if isinstance(step, dict):
                                    run_cmd = step.get("run")
                                    uses = step.get("uses")
                                    if run_cmd and isinstance(run_cmd, str):
                                        first_line = run_cmd.strip().split("\n")[0]
                                        if first_line not in steps:
                                            steps.append(first_line)
                                    elif uses and isinstance(uses, str):
                                        action_name = uses.split("@")[0]
                                        if action_name not in steps:
                                            steps.append(action_name)
            return steps[:20]

        full_path = repo_path / config_path
        if full_path.is_file():
            content = self.read_file(full_path)
            if content:
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("- ") and ("run" in stripped or "script" in stripped):
                        steps.append(stripped[:80])

        return steps[:20]

    def _detect_deployment_targets(self, repo_path: Path) -> list[str]:
        targets: list[str] = []
        if (repo_path / "Dockerfile").exists() or list(repo_path.glob("*.Dockerfile")):
            targets.append("docker")
        if (repo_path / "docker-compose.yml").exists() or (repo_path / "docker-compose.yaml").exists():
            targets.append("docker-compose")
        if (repo_path / "serverless.yml").exists() or (repo_path / "serverless.yaml").exists():
            targets.append("serverless")
        if (repo_path / "vercel.json").exists():
            targets.append("vercel")
        if (repo_path / "netlify.toml").exists():
            targets.append("netlify")
        if (repo_path / "fly.toml").exists():
            targets.append("fly.io")
        if (repo_path / "render.yaml").exists():
            targets.append("render")
        if (repo_path / "app.yaml").exists() or (repo_path / "app.yml").exists():
            targets.append("google-app-engine")
        if (repo_path / "Procfile").exists():
            targets.append("heroku")
        if (repo_path / "k8s").is_dir() or (repo_path / "kubernetes").is_dir():
            targets.append("kubernetes")
        if (repo_path / "railway.toml").exists() or (repo_path / "railway.json").exists():
            targets.append("railway")
        if (repo_path / "sst.config.ts").exists():
            targets.append("sst")
        if (repo_path / "Pulumi.yaml").exists():
            targets.append("pulumi")
        if (repo_path / "cdk.json").exists():
            targets.append("aws-cdk")
        if (repo_path / "Chart.yaml").exists():
            targets.append("helm")
        if (repo_path / "kustomization.yaml").exists():
            targets.append("kustomize")
        return targets

    def _detect_required_checks(
        self, _repo_path: Path, _platform: str | None, _config_path: str | None
    ) -> list[str]:
        # Branch protection / required status checks are not available offline; workflow
        # job names are not equivalent and would mislead consumers.
        return []


register(CICDAnalyzer())
