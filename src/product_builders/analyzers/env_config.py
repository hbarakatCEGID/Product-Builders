"""Environment & Configuration Analyzer — Dimension 8 (HIGH IMPACT).

Detects config approach (dotenv, yaml, vault), env files, Docker setup,
feature flags system, and config directories.
"""

from __future__ import annotations

from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, EnvConfigResult


class EnvConfigAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Environment & Config Analyzer"

    @property
    def dimension(self) -> str:
        return "env_config"

    def analyze(self, repo_path: Path, *, index=None) -> EnvConfigResult:
        config_approach = self._detect_config_approach(repo_path)
        env_files = self._detect_env_files(repo_path)
        has_docker, dockerfile, compose = self._detect_docker(repo_path)
        feature_flags = self._detect_feature_flags(repo_path)
        config_dirs = self._detect_config_dirs(repo_path)

        deps = self._collect_dep_names(repo_path)

        # C26: Kubernetes / orchestration detection
        kubernetes_detected = False
        k8s_indicators = ["k8s", "kubernetes", "Chart.yaml", "kustomization.yaml", "skaffold.yaml"]
        for indicator in k8s_indicators:
            if (repo_path / indicator).exists():
                kubernetes_detected = True
                break
        if not kubernetes_detected:
            for d in ("k8s", "kubernetes", "deploy", "infra"):
                if (repo_path / d).is_dir():
                    yamls = list((repo_path / d).glob("*.yaml")) + list((repo_path / d).glob("*.yml"))
                    if yamls:
                        kubernetes_detected = True
                        break

        # C26: Secrets management detection
        secrets_mgmt = None
        secrets_indicators = {
            "@aws-sdk/client-secrets-manager": "aws-secrets-manager",
            "@azure/keyvault-secrets": "azure-key-vault",
            "@google-cloud/secret-manager": "gcp-secret-manager",
            "infisical-sdk": "infisical",
            "@infisical/sdk": "infisical",
        }
        for dep, name in secrets_indicators.items():
            if dep in deps:
                secrets_mgmt = name
                break
        if not secrets_mgmt:
            file_indicators = {
                "doppler.yaml": "doppler",
                ".infisical.json": "infisical",
            }
            for f, name in file_indicators.items():
                if (repo_path / f).exists():
                    secrets_mgmt = name
                    break

        result = EnvConfigResult(
            status=AnalysisStatus.SUCCESS,
            config_approach=config_approach,
            env_files=env_files,
            has_docker=has_docker,
            dockerfile_path=dockerfile,
            docker_compose_path=compose,
            feature_flags_system=feature_flags,
            config_directories=config_dirs,
            kubernetes_detected=kubernetes_detected,
            secrets_management=secrets_mgmt,
        )

        anti_patterns = []
        if result.kubernetes_detected and not result.secrets_management:
            anti_patterns.append("HIGH: Kubernetes detected but no secrets management — secrets may be in plain manifests")
        if result.has_docker and not result.config_approach:
            anti_patterns.append("MEDIUM: Docker detected but no config approach — env vars may be hardcoded")
        if not result.feature_flags_system:
            anti_patterns.append("LOW: no feature flag system detected — feature rollout requires redeployment")
        result.anti_patterns = anti_patterns

        return result

    def _detect_config_approach(self, repo_path: Path) -> str | None:
        env_files = list(repo_path.glob(".env*"))
        if env_files:
            return "dotenv"
        if (repo_path / "config").is_dir():
            yaml_configs = list((repo_path / "config").glob("*.yaml")) + list((repo_path / "config").glob("*.yml"))
            if yaml_configs:
                return "yaml"
            json_configs = list((repo_path / "config").glob("*.json"))
            if json_configs:
                return "json"
        if (repo_path / "vault.hcl").exists():
            return "vault"
        if (repo_path / "application.properties").exists() or (repo_path / "application.yml").exists():
            return "spring-config"
        if (repo_path / "appsettings.json").exists():
            return "dotnet-config"
        return None

    def _detect_env_files(self, repo_path: Path) -> list[str]:
        env_patterns = [".env", ".env.example", ".env.local", ".env.development",
                        ".env.production", ".env.test", ".env.staging"]
        found: list[str] = []
        for pattern in env_patterns:
            if (repo_path / pattern).exists():
                found.append(pattern)
        return found

    def _detect_docker(self, repo_path: Path) -> tuple[bool, str | None, str | None]:
        dockerfile: str | None = None
        compose: str | None = None

        if (repo_path / "Dockerfile").exists():
            dockerfile = "Dockerfile"
        else:
            dockerfiles = list(repo_path.glob("*.Dockerfile"))
            if dockerfiles:
                dockerfile = dockerfiles[0].name

        compose_names = [
            "docker-compose.yml", "docker-compose.yaml",
            "docker-compose.dev.yml", "docker-compose.dev.yaml",
            "compose.yml", "compose.yaml",
        ]
        for name in compose_names:
            if (repo_path / name).exists():
                compose = name
                break

        has_docker = dockerfile is not None or compose is not None
        return has_docker, dockerfile, compose

    def _detect_feature_flags(self, repo_path: Path) -> str | None:
        pkg = self.read_json(repo_path / "package.json")
        if pkg:
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "launchdarkly-js-client-sdk" in deps or "@launchdarkly/node-server-sdk" in deps:
                return "launchdarkly"
            if "flagsmith" in deps:
                return "flagsmith"
            if "@unleash/proxy-client-react" in deps or "unleash-client" in deps:
                return "unleash"
            if "@growthbook/growthbook-react" in deps:
                return "growthbook"
            if "posthog-js" in deps:
                return "posthog"
            if "statsig-js" in deps or "statsig-node" in deps:
                return "statsig"
            if "@splitsoftware/splitio" in deps:
                return "split.io"
            if "@devcycle/nodejs-server-sdk" in deps:
                return "devcycle"
            if "@flipt-io/flipt" in deps:
                return "flipt"
            if "@openfeature/server-sdk" in deps or "@openfeature/web-sdk" in deps:
                return "openfeature"
            if "configcat-js" in deps or "configcat-node" in deps:
                return "configcat"
        req = repo_path / "requirements.txt"
        if req.exists():
            content = self.read_file(req)
            if content:
                if "django-waffle" in content:
                    return "django-waffle"
                if "flipper" in content:
                    return "flipper"
        return None

    def _detect_config_dirs(self, repo_path: Path) -> list[str]:
        candidates = ["config", "conf", "cfg", "settings", "src/config", "src/settings"]
        return [d for d in candidates if (repo_path / d).is_dir()]


register(EnvConfigAnalyzer())
