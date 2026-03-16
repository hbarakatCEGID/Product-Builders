"""Dependency Analyzer — Dimension 4 (HIGH IMPACT).

Extracts core and dev dependencies, key libraries, version constraints,
and identifies the dependency manifest files and lock files.
"""

from __future__ import annotations

import re
from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer
from product_builders.analyzers.registry import register
from product_builders.models.analysis import (
    AnalysisStatus,
    DependenciesResult,
    DependencyInfo,
)

KNOWN_CATEGORIES: dict[str, str] = {
    # JavaScript/TypeScript
    "react": "ui-framework", "vue": "ui-framework", "@angular/core": "ui-framework",
    "svelte": "ui-framework", "next": "web-framework", "nuxt": "web-framework",
    "express": "web-framework", "fastify": "web-framework", "@nestjs/core": "web-framework",
    "axios": "http-client", "node-fetch": "http-client", "ky": "http-client",
    "prisma": "orm", "@prisma/client": "orm", "typeorm": "orm", "sequelize": "orm",
    "mongoose": "orm", "drizzle-orm": "orm", "knex": "query-builder",
    "jest": "testing", "vitest": "testing", "mocha": "testing", "cypress": "e2e-testing",
    "playwright": "e2e-testing", "@testing-library/react": "testing",
    "tailwindcss": "styling", "styled-components": "styling", "@emotion/react": "styling",
    "sass": "styling", "less": "styling",
    "zod": "validation", "joi": "validation", "yup": "validation",
    "redux": "state-management", "zustand": "state-management", "mobx": "state-management",
    "@tanstack/react-query": "data-fetching", "swr": "data-fetching",
    "react-hook-form": "forms", "formik": "forms",
    "i18next": "i18n", "react-intl": "i18n", "vue-i18n": "i18n",
    "winston": "logging", "pino": "logging", "@sentry/node": "monitoring",
    "eslint": "linting", "prettier": "formatting", "typescript": "language",
    # Python
    "django": "web-framework", "flask": "web-framework", "fastapi": "web-framework",
    "sqlalchemy": "orm", "alembic": "migration", "celery": "task-queue",
    "pytest": "testing", "requests": "http-client", "httpx": "http-client",
    "pydantic": "validation", "sentry-sdk": "monitoring",
    "ruff": "linting", "black": "formatting", "mypy": "type-checking",
}


class DependencyAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Dependency Analyzer"

    @property
    def dimension(self) -> str:
        return "dependencies"

    def analyze(self, repo_path: Path) -> DependenciesResult:
        deps: list[DependencyInfo] = []
        manifest_files: list[str] = []
        lock_file: str | None = None

        # package.json
        pkg = repo_path / "package.json"
        if pkg.exists():
            manifest_files.append("package.json")
            data = self.read_json(pkg)
            if data:
                for section, is_dev in [("dependencies", False), ("devDependencies", True), ("peerDependencies", False)]:
                    for name, version in data.get(section, {}).items():
                        deps.append(DependencyInfo(
                            name=name,
                            version=version,
                            is_dev=is_dev,
                            category=KNOWN_CATEGORIES.get(name, ""),
                        ))

        # requirements.txt / requirements-dev.txt
        for req_file in sorted(repo_path.glob("requirements*.txt")):
            manifest_files.append(req_file.name)
            is_dev = "dev" in req_file.stem
            content = self.read_file(req_file)
            if content:
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith(("#", "-")):
                        continue
                    parts = re.split(r"([><=!~\[])", line, maxsplit=1)
                    name = parts[0].strip()
                    version = line[len(name):].strip() if len(parts) > 1 else None
                    if name:
                        deps.append(DependencyInfo(
                            name=name,
                            version=version,
                            is_dev=is_dev,
                            category=KNOWN_CATEGORIES.get(name.lower(), ""),
                        ))

        # pyproject.toml
        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists():
            manifest_files.append("pyproject.toml")

        # Pipfile
        pipfile = repo_path / "Pipfile"
        if pipfile.exists():
            manifest_files.append("Pipfile")

        # pom.xml
        pom = repo_path / "pom.xml"
        if pom.exists():
            manifest_files.append("pom.xml")

        # *.csproj
        for csproj in self.find_files(repo_path, "*.csproj"):
            rel = str(csproj.relative_to(repo_path))
            manifest_files.append(rel)

        # Detect lock file
        lock_files = {
            "package-lock.json": "package-lock.json",
            "yarn.lock": "yarn.lock",
            "pnpm-lock.yaml": "pnpm-lock.yaml",
            "Pipfile.lock": "Pipfile.lock",
            "poetry.lock": "poetry.lock",
            "uv.lock": "uv.lock",
            "Cargo.lock": "Cargo.lock",
            "go.sum": "go.sum",
            "Gemfile.lock": "Gemfile.lock",
        }
        for lf_name, lf_value in lock_files.items():
            if (repo_path / lf_name).exists():
                lock_file = lf_value
                break

        return DependenciesResult(
            status=AnalysisStatus.SUCCESS,
            dependencies=deps,
            dependency_manifest_files=manifest_files,
            lock_file=lock_file,
        )


register(DependencyAnalyzer())
