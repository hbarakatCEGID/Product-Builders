"""Security Analyzer — Dimension 12 (MEDIUM IMPACT).

Detects input validation libraries, CORS configuration, secrets management,
CSP headers, security middleware, and vulnerability scanning tools.
"""

from __future__ import annotations

from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer
from product_builders.analyzers.deps import (
    SECURITY_MIDDLEWARE_PACKAGE_TO_NAME,
    SECURITY_PYPROJECT_HINTS,
    VALIDATION_PACKAGE_TO_NAME,
)
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, SecurityResult


class SecurityAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Security Analyzer"

    @property
    def dimension(self) -> str:
        return "security"

    def analyze(self, repo_path: Path, *, index=None) -> SecurityResult:
        input_validation = self._detect_validation(repo_path)
        cors = self._detect_cors(repo_path)
        secrets_mgmt = self._detect_secrets_management(repo_path)
        csp = self._detect_csp(repo_path)
        middleware = self._detect_middleware(repo_path)
        vuln_scanner = self._detect_vuln_scanner(repo_path)

        result = SecurityResult(
            status=AnalysisStatus.SUCCESS,
            input_validation=input_validation,
            cors_config=cors,
            secrets_management=secrets_mgmt,
            csp_headers=csp,
            security_middleware=middleware,
            vulnerability_scanning=vuln_scanner,
        )

        # Anti-pattern detection
        anti_patterns = []

        # Check if .env is in .gitignore
        gitignore = self.read_file(repo_path / ".gitignore")
        if gitignore and ".env" not in gitignore:
            if (repo_path / ".env").exists():
                anti_patterns.append("CRITICAL: .env file may not be gitignored — secrets at risk")

        # No vulnerability scanning
        if result.vulnerability_scanning is None:
            anti_patterns.append("MEDIUM: no dependency vulnerability scanning detected (Snyk, Dependabot, Renovate, etc.)")

        # No input validation
        if result.input_validation is None:
            anti_patterns.append("HIGH: no input validation library detected")

        # No security headers (CSP)
        if not result.csp_headers:
            anti_patterns.append("MEDIUM: no Content-Security-Policy (CSP) headers detected")

        # No secrets management beyond .env
        if result.secrets_management is None:
            env_files = [f for f in (repo_path / ".env").parent.iterdir() if f.name.startswith(".env")] if (repo_path / ".env").parent.exists() else []
            if len(env_files) > 2:
                anti_patterns.append("MEDIUM: multiple .env files but no secrets management tool (Vault, AWS SM, etc.)")

        result.anti_patterns = anti_patterns
        return result

    def _detect_validation(self, repo_path: Path) -> str | None:
        deps = self.collect_dependency_names(
            repo_path, pyproject_substrings=SECURITY_PYPROJECT_HINTS
        )
        for lib, name in VALIDATION_PACKAGE_TO_NAME.items():
            if lib in deps:
                return name
        return None

    def _detect_cors(self, repo_path: Path) -> str | None:
        for name in ("cors.json", "cors.yaml", "cors.yml"):
            if (repo_path / name).exists():
                return name
        pkg = self.read_json(repo_path / "package.json")
        if pkg:
            all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "cors" in all_deps:
                return "cors (npm)"
        settings = repo_path / "settings.py"
        if not settings.exists():
            for candidate in (repo_path / "src").rglob("settings.py") if (repo_path / "src").is_dir() else []:
                settings = candidate
                break
        if settings.exists():
            content = self.read_file(settings)
            if content and "CORS" in content:
                return "django-cors-headers"
        return None

    def _detect_secrets_management(self, repo_path: Path) -> str | None:
        if (repo_path / ".env.vault").exists():
            return "dotenv-vault"
        if (repo_path / "vault.hcl").exists() or (repo_path / ".vault-token").exists():
            return "hashicorp-vault"
        if (repo_path / ".sops.yaml").exists():
            return "sops"
        if (repo_path / "doppler.yaml").exists():
            return "doppler"
        if (repo_path / ".infisical.json").exists():
            return "infisical"
        return None

    def _detect_csp(self, repo_path: Path) -> bool:
        pkg = self.read_json(repo_path / "package.json")
        if pkg:
            all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "helmet" in all_deps:
                return True
        for py_file in list((repo_path / "src").rglob("*.py"))[:100] if (repo_path / "src").is_dir() else []:
            content = self.read_file(py_file)
            if content and ("Content-Security-Policy" in content or "CSP_" in content):
                return True
        return False

    def _detect_middleware(self, repo_path: Path) -> list[str]:
        found: list[str] = []
        deps = self.collect_dependency_names(
            repo_path, pyproject_substrings=SECURITY_PYPROJECT_HINTS
        )
        for lib, name in SECURITY_MIDDLEWARE_PACKAGE_TO_NAME.items():
            if lib in deps and name not in found:
                found.append(name)
        return found

    def _detect_vuln_scanner(self, repo_path: Path) -> str | None:
        if (repo_path / ".snyk").exists():
            return "snyk"
        if (repo_path / ".bandit").exists() or (repo_path / "bandit.yaml").exists():
            return "bandit"
        if (repo_path / ".semgrep.yml").exists() or (repo_path / ".semgrep").is_dir():
            return "semgrep"
        if (repo_path / ".github" / "dependabot.yml").exists():
            return "dependabot"
        if (repo_path / "renovate.json").exists() or (repo_path / ".renovaterc").exists():
            return "renovate"
        if (repo_path / ".trivyignore").exists():
            return "trivy"
        if (repo_path / ".brakeman.yml").exists():
            return "brakeman"
        if (repo_path / ".github" / "codeql").is_dir():
            return "codeql"
        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists():
            content = self.read_file(pyproject)
            if content and "bandit" in content:
                return "bandit"
        return None


register(SecurityAnalyzer())
