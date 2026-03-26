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
    # RPC
    "@trpc/client": "rpc", "@trpc/server": "rpc",
    # Additional web frameworks
    "hono": "web-framework", "elysia": "web-framework", "astro": "web-framework",
    # Additional testing / validation / styling
    "@playwright/test": "e2e-testing",
    "valibot": "validation",
    "@vanilla-extract/css": "styling", "@pandacss/dev": "styling", "unocss": "styling",
}


class DependencyAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Dependency Analyzer"

    @property
    def dimension(self) -> str:
        return "dependencies"

    def analyze(self, repo_path: Path, *, index=None) -> DependenciesResult:
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

        # pyproject.toml — parse [project.dependencies] and [tool.poetry.dependencies]
        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists():
            manifest_files.append("pyproject.toml")
            content = self.read_file(pyproject)
            if content:
                in_deps = False
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped in (
                        "[project.dependencies]",
                        "[tool.poetry.dependencies]",
                    ):
                        in_deps = True
                        continue
                    if stripped.startswith("[") and in_deps:
                        in_deps = False
                        continue
                    if in_deps and stripped and not stripped.startswith("#"):
                        # Handle both "requests>=2.28" and name = "^1.0"
                        parts = re.split(r"[>=<~^!=]", stripped, maxsplit=1)
                        dep_name = parts[0].strip().strip('"').strip("'")
                        if dep_name and dep_name != "python":
                            deps.append(DependencyInfo(
                                name=dep_name,
                                category=KNOWN_CATEGORIES.get(dep_name.lower(), ""),
                            ))

        # Pipfile
        pipfile = repo_path / "Pipfile"
        if pipfile.exists():
            manifest_files.append("Pipfile")

        # Gemfile — parse gem declarations
        gemfile = repo_path / "Gemfile"
        if gemfile.exists():
            manifest_files.append("Gemfile")
            content = self.read_file(gemfile)
            if content:
                for line in content.splitlines():
                    match = re.match(r"""gem\s+['"]([^'"]+)['"]""", line.strip())
                    if match:
                        deps.append(DependencyInfo(
                            name=match.group(1),
                            category=KNOWN_CATEGORIES.get(match.group(1).lower(), ""),
                        ))

        # go.mod — parse require blocks
        go_mod = repo_path / "go.mod"
        if go_mod.exists():
            manifest_files.append("go.mod")
            content = self.read_file(go_mod)
            if content:
                in_require = False
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped == "require (" or stripped.startswith("require ("):
                        in_require = True
                        continue
                    if stripped == ")" and in_require:
                        in_require = False
                        continue
                    if in_require and stripped and not stripped.startswith("//"):
                        parts = stripped.split()
                        if parts:
                            deps.append(DependencyInfo(name=parts[0]))
                    elif stripped.startswith("require ") and "(" not in stripped:
                        parts = stripped.split()
                        if len(parts) >= 2:
                            deps.append(DependencyInfo(name=parts[1]))

        # Cargo.toml — parse [dependencies] and [dev-dependencies]
        cargo = repo_path / "Cargo.toml"
        if cargo.exists():
            manifest_files.append("Cargo.toml")
            content = self.read_file(cargo)
            if content:
                in_deps = False
                is_dev = False
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped == "[dependencies]":
                        in_deps = True
                        is_dev = False
                        continue
                    if stripped == "[dev-dependencies]":
                        in_deps = True
                        is_dev = True
                        continue
                    if stripped.startswith("[") and in_deps:
                        in_deps = False
                        continue
                    if in_deps and "=" in stripped and not stripped.startswith("#"):
                        dep_name = stripped.split("=")[0].strip()
                        if dep_name:
                            deps.append(DependencyInfo(name=dep_name, is_dev=is_dev))

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

        result = DependenciesResult(
            status=AnalysisStatus.SUCCESS,
            dependencies=deps,
            dependency_manifest_files=manifest_files,
            lock_file=lock_file,
        )

        anti_patterns = []
        if not result.lock_file:
            anti_patterns.append("HIGH: no lock file found — dependency versions will not be reproducible")
        if not result.dependency_manifest_files:
            anti_patterns.append("HIGH: no dependency manifest file detected")
        result.anti_patterns = anti_patterns

        return result


register(DependencyAnalyzer())
