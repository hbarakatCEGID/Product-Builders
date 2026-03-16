"""Conventions Analyzer — Dimension 11 (MEDIUM IMPACT).

Detects linter and formatter configurations, editorconfig,
import ordering, and naming conventions from config files.
"""

from __future__ import annotations

from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, ConventionsResult

LINTER_CONFIGS: dict[str, str] = {
    ".eslintrc": "eslint",
    ".eslintrc.js": "eslint",
    ".eslintrc.cjs": "eslint",
    ".eslintrc.json": "eslint",
    ".eslintrc.yaml": "eslint",
    ".eslintrc.yml": "eslint",
    "eslint.config.js": "eslint",
    "eslint.config.mjs": "eslint",
    "eslint.config.cjs": "eslint",
    "eslint.config.ts": "eslint",
    ".pylintrc": "pylint",
    "pylintrc": "pylint",
    ".flake8": "flake8",
    "setup.cfg": "flake8",  # may contain flake8 config
    "ruff.toml": "ruff",
    ".rubocop.yml": "rubocop",
    "checkstyle.xml": "checkstyle",
    ".stylelintrc": "stylelint",
    ".stylelintrc.json": "stylelint",
    "stylelint.config.js": "stylelint",
    "biome.json": "biome",
    "biome.jsonc": "biome",
}

FORMATTER_CONFIGS: dict[str, str] = {
    ".prettierrc": "prettier",
    ".prettierrc.js": "prettier",
    ".prettierrc.cjs": "prettier",
    ".prettierrc.json": "prettier",
    ".prettierrc.yaml": "prettier",
    ".prettierrc.yml": "prettier",
    ".prettierrc.toml": "prettier",
    "prettier.config.js": "prettier",
    "prettier.config.cjs": "prettier",
    "prettier.config.ts": "prettier",
    "biome.json": "biome",
    "biome.jsonc": "biome",
}


class ConventionsAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Conventions Analyzer"

    @property
    def dimension(self) -> str:
        return "conventions"

    def analyze(self, repo_path: Path) -> ConventionsResult:
        linter, linter_path = self._detect_linter(repo_path)
        formatter, formatter_path = self._detect_formatter(repo_path)
        editorconfig = self._detect_editorconfig(repo_path)
        naming = self._detect_naming_convention(repo_path)
        file_naming = self._detect_file_naming(repo_path)

        # Ruff in pyproject.toml
        if not linter:
            pyproject = repo_path / "pyproject.toml"
            if pyproject.exists():
                content = self.read_file(pyproject)
                if content and "[tool.ruff" in content:
                    linter = "ruff"
                    linter_path = "pyproject.toml"
                elif content and "[tool.pylint" in content:
                    linter = "pylint"
                    linter_path = "pyproject.toml"

        # Prettier in package.json
        if not formatter:
            pkg = repo_path / "package.json"
            if pkg.exists():
                data = self.read_json(pkg)
                if data and "prettier" in data:
                    formatter = "prettier"
                    formatter_path = "package.json"

        # Black in pyproject.toml
        if not formatter:
            pyproject = repo_path / "pyproject.toml"
            if pyproject.exists():
                content = self.read_file(pyproject)
                if content and "[tool.black" in content:
                    formatter = "black"
                    formatter_path = "pyproject.toml"

        return ConventionsResult(
            status=AnalysisStatus.SUCCESS,
            linter=linter,
            linter_config_path=linter_path,
            formatter=formatter,
            formatter_config_path=formatter_path,
            editorconfig_path=editorconfig,
            naming_convention=naming,
            file_naming_convention=file_naming,
        )

    def _detect_linter(self, repo_path: Path) -> tuple[str | None, str | None]:
        for filename, linter_name in LINTER_CONFIGS.items():
            if (repo_path / filename).exists():
                return linter_name, filename
        return None, None

    def _detect_formatter(self, repo_path: Path) -> tuple[str | None, str | None]:
        for filename, fmt_name in FORMATTER_CONFIGS.items():
            if (repo_path / filename).exists():
                return fmt_name, filename
        return None, None

    def _detect_editorconfig(self, repo_path: Path) -> str | None:
        if (repo_path / ".editorconfig").exists():
            return ".editorconfig"
        return None

    def _detect_naming_convention(self, repo_path: Path) -> str | None:
        """Infer naming convention from linter config if available."""
        for eslint_file in [".eslintrc.json", ".eslintrc.js", ".eslintrc"]:
            path = repo_path / eslint_file
            if path.exists():
                content = self.read_file(path)
                if content:
                    if "camelCase" in content or "camelcase" in content:
                        return "camelCase"
                    if "PascalCase" in content:
                        return "PascalCase"
        return None

    def _detect_file_naming(self, repo_path: Path) -> str | None:
        """Sample source files to detect file naming convention."""
        src_dir = repo_path / "src"
        scan_dir = src_dir if src_dir.is_dir() else repo_path

        samples: list[str] = []
        count = 0
        for path in scan_dir.rglob("*"):
            if count >= 50:
                break
            if path.is_file() and path.suffix in (".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".cs"):
                skip_dirs = {"node_modules", ".git", "__pycache__", "dist", "build", ".next"}
                if not any(s in path.parts for s in skip_dirs):
                    samples.append(path.stem)
                    count += 1

        if not samples:
            return None

        kebab = sum(1 for s in samples if "-" in s and "_" not in s and s == s.lower())
        pascal = sum(1 for s in samples if s[0:1].isupper() and "-" not in s and "_" not in s)
        camel = sum(1 for s in samples if s[0:1].islower() and "-" not in s and "_" not in s and any(c.isupper() for c in s))
        snake = sum(1 for s in samples if "_" in s and s == s.lower())

        scores = {"kebab-case": kebab, "PascalCase": pascal, "camelCase": camel, "snake_case": snake}
        best = max(scores, key=lambda k: scores[k])
        if scores[best] > len(samples) * 0.3:
            return best
        return None


register(ConventionsAnalyzer())
