"""Tech Stack Analyzer — Dimension 1 (CRITICAL).

Detects languages, frameworks, build tools, package managers,
and runtime versions by scanning file extensions, config files,
and dependency manifests.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from product_builders.analyzers.base import SKIP_DIRS, BaseAnalyzer
from product_builders.analyzers.registry import register
from product_builders.models.analysis import (
    AnalysisStatus,
    FrameworkInfo,
    TechStackResult,
)

LANGUAGE_EXTENSIONS: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".scala": "Scala",
    ".clj": "Clojure",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".dart": "Dart",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".less": "LESS",
    ".sql": "SQL",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".r": "R",
    ".m": "Objective-C",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
}

FRAMEWORK_DETECTORS: dict[str, dict] = {
    # JavaScript/TypeScript frameworks
    "next": {"dep_names": ["next"], "category": "web"},
    "react": {"dep_names": ["react"], "category": "web"},
    "vue": {"dep_names": ["vue"], "category": "web"},
    "nuxt": {"dep_names": ["nuxt"], "category": "web"},
    "angular": {"dep_names": ["@angular/core"], "category": "web"},
    "svelte": {"dep_names": ["svelte"], "category": "web"},
    "express": {"dep_names": ["express"], "category": "web"},
    "fastify": {"dep_names": ["fastify"], "category": "web"},
    "nestjs": {"dep_names": ["@nestjs/core"], "category": "web"},
    "remix": {"dep_names": ["@remix-run/node", "@remix-run/react"], "category": "web"},
    "gatsby": {"dep_names": ["gatsby"], "category": "web"},
    "electron": {"dep_names": ["electron"], "category": "desktop"},
    # Python frameworks
    "django": {"dep_names": ["django", "Django"], "category": "web"},
    "flask": {"dep_names": ["flask", "Flask"], "category": "web"},
    "fastapi": {"dep_names": ["fastapi", "FastAPI"], "category": "web"},
    "starlette": {"dep_names": ["starlette"], "category": "web"},
    "celery": {"dep_names": ["celery"], "category": "task-queue"},
    # Java/Kotlin frameworks
    "spring-boot": {"dep_names": ["spring-boot", "org.springframework.boot"], "category": "web"},
    "quarkus": {"dep_names": ["quarkus"], "category": "web"},
    "micronaut": {"dep_names": ["micronaut"], "category": "web"},
    # .NET frameworks
    "aspnet": {"dep_names": ["Microsoft.AspNetCore"], "category": "web"},
    "blazor": {"dep_names": ["Microsoft.AspNetCore.Components"], "category": "web"},
    # Ruby frameworks
    "rails": {"dep_names": ["rails"], "category": "web"},
    "sinatra": {"dep_names": ["sinatra"], "category": "web"},
    # Additional JS/TS frameworks
    "astro": {"dep_names": ["astro"], "category": "web"},
    "hono": {"dep_names": ["hono"], "category": "web"},
    "elysia": {"dep_names": ["elysia", "@elysiajs/core"], "category": "web"},
    "sveltekit": {"dep_names": ["@sveltejs/kit"], "category": "web"},
    "solidjs": {"dep_names": ["solid-js"], "category": "web"},
    "solidstart": {"dep_names": ["@solidjs/start"], "category": "web"},
    "qwik": {"dep_names": ["@builder.io/qwik"], "category": "web"},
    "qwikcity": {"dep_names": ["@builder.io/qwik-city"], "category": "web"},
    "h3": {"dep_names": ["h3"], "category": "web"},
    "nitro": {"dep_names": ["nitropack"], "category": "web"},
    "tanstack-start": {"dep_names": ["@tanstack/start"], "category": "web"},
    "analog": {"dep_names": ["@analogjs/platform"], "category": "web"},
    # Additional Python frameworks
    "litestar": {"dep_names": ["litestar"], "category": "web"},
    "fasthtml": {"dep_names": ["python-fasthtml", "fasthtml"], "category": "web"},
    "quart": {"dep_names": ["quart"], "category": "web"},
    "sanic": {"dep_names": ["sanic"], "category": "web"},
}

BUILD_TOOL_FILES: dict[str, str] = {
    "Makefile": "make",
    "CMakeLists.txt": "cmake",
    "Gruntfile.js": "grunt",
    "gulpfile.js": "gulp",
    "webpack.config.js": "webpack",
    "webpack.config.ts": "webpack",
    "vite.config.js": "vite",
    "vite.config.ts": "vite",
    "rollup.config.js": "rollup",
    "esbuild.config.js": "esbuild",
    "turbo.json": "turborepo",
    "nx.json": "nx",
    "build.gradle": "gradle",
    "build.gradle.kts": "gradle",
    "pom.xml": "maven",
    "build.sbt": "sbt",
    "Cargo.toml": "cargo",
    "Gemfile": "bundler",
    "mix.exs": "mix",
    "go.mod": "go-modules",
    "deno.json": "deno",
    "deno.jsonc": "deno",
    "bunfig.toml": "bun",
}

PACKAGE_MANAGER_FILES: dict[str, str] = {
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "bun.lockb": "bun",
    "Pipfile.lock": "pipenv",
    "poetry.lock": "poetry",
    "pdm.lock": "pdm",
    "uv.lock": "uv",
    "requirements.txt": "pip",
    "Gemfile.lock": "bundler",
    "go.sum": "go-modules",
    "Cargo.lock": "cargo",
    "packages.lock.json": "nuget",
    "paket.lock": "paket",
    "composer.lock": "composer",
    "deno.lock": "deno",
    "pixi.lock": "pixi",
    "pixi.toml": "pixi",
    "Package.swift": "swift-pm",
    "pubspec.lock": "pub",
    "Podfile.lock": "cocoapods",
}


class TechStackAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Tech Stack Analyzer"

    @property
    def dimension(self) -> str:
        return "tech_stack"

    def analyze(self, repo_path: Path, *, index=None) -> TechStackResult:
        languages = self._detect_languages(repo_path)
        primary = max(languages, key=languages.get) if languages else None
        frameworks = self._detect_frameworks(repo_path)
        build_tools = self._detect_build_tools(repo_path)
        pkg_managers = self._detect_package_managers(repo_path)
        runtime_versions = self._detect_runtime_versions(repo_path)

        result = TechStackResult(
            status=AnalysisStatus.SUCCESS,
            languages=languages,
            primary_language=primary,
            frameworks=frameworks,
            build_tools=build_tools,
            package_managers=pkg_managers,
            runtime_versions=runtime_versions,
        )

        anti_patterns = []
        if not result.languages:
            anti_patterns.append("CRITICAL: no source code files detected")
        if not result.frameworks:
            anti_patterns.append("MEDIUM: no framework detected — project structure may be unclear to AI assistants")
        result.anti_patterns = anti_patterns

        return result

    # Directories excluded from language % to avoid skewing by tests/docs/examples
    _LANG_EXCLUDE_DIRS: frozenset[str] = frozenset({
        "tests", "test", "__tests__", "spec", "specs",
        "docs", "doc", "examples", "example", "fixtures",
        "e2e", "cypress", "playwright",
    })

    def _detect_languages(self, repo_path: Path) -> dict[str, float]:
        counter: Counter[str] = Counter()
        total = 0
        for path in repo_path.rglob("*"):
            if any(skip in path.parts for skip in SKIP_DIRS):
                continue
            if any(excl in path.parts for excl in self._LANG_EXCLUDE_DIRS):
                continue
            if path.is_file():
                lang = LANGUAGE_EXTENSIONS.get(path.suffix.lower())
                if lang:
                    counter[lang] += 1
                    total += 1

        if total == 0:
            return {}
        return {lang: round(count / total * 100, 1) for lang, count in counter.most_common()}

    def _detect_frameworks(self, repo_path: Path) -> list[FrameworkInfo]:
        dep_names = set()

        # Collect dependency names from various manifests
        pkg_json = repo_path / "package.json"
        if pkg_json.exists():
            data = self.read_json(pkg_json)
            if data:
                for section in ["dependencies", "devDependencies", "peerDependencies"]:
                    dep_names.update(data.get(section, {}).keys())

        # Python: requirements.txt, pyproject.toml, Pipfile
        for req_file in self.find_files(repo_path, "requirements*.txt"):
            content = self.read_file(req_file)
            if content:
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith(("#", "-")):
                        name = re.split(r"[><=!~\[]", line)[0].strip()
                        if name:
                            dep_names.add(name)

        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists():
            content = self.read_file(pyproject)
            if content:
                in_deps = False
                for line in content.splitlines():
                    if "dependencies" in line and "=" in line:
                        in_deps = True
                        continue
                    if in_deps:
                        if line.strip().startswith("]"):
                            in_deps = False
                            continue
                        match = re.search(r'"([^"]+)"', line)
                        if match:
                            name = re.split(r"[><=!~\[]", match.group(1))[0].strip()
                            if name:
                                dep_names.add(name)

        # Java: pom.xml basic detection
        pom = repo_path / "pom.xml"
        if pom.exists():
            content = self.read_file(pom)
            if content:
                for match in re.finditer(r"<artifactId>([^<]+)</artifactId>", content):
                    dep_names.add(match.group(1))

        # .NET: *.csproj basic detection
        for csproj in self.find_files(repo_path, "*.csproj"):
            content = self.read_file(csproj)
            if content:
                for match in re.finditer(r'Include="([^"]+)"', content):
                    dep_names.add(match.group(1))

        frameworks: list[FrameworkInfo] = []
        for fw_name, cfg in FRAMEWORK_DETECTORS.items():
            if any(dep in dep_names for dep in cfg["dep_names"]):
                version = None
                pkg_data = self.read_json(pkg_json) if pkg_json.exists() else None
                if pkg_data:
                    for dep in cfg["dep_names"]:
                        for section in ["dependencies", "devDependencies"]:
                            v = pkg_data.get(section, {}).get(dep)
                            if v:
                                version = v
                                break
                        if version:
                            break

                frameworks.append(FrameworkInfo(
                    name=fw_name,
                    version=self._normalize_version(version) if version else None,
                    category=cfg["category"],
                ))

        return frameworks

    def _detect_build_tools(self, repo_path: Path) -> list[str]:
        tools: list[str] = []
        for filename, tool in BUILD_TOOL_FILES.items():
            if (repo_path / filename).exists():
                tools.append(tool)
        return tools

    def _detect_package_managers(self, repo_path: Path) -> list[str]:
        managers: list[str] = []
        for filename, manager in PACKAGE_MANAGER_FILES.items():
            if (repo_path / filename).exists():
                managers.append(manager)
        return managers

    def _detect_runtime_versions(self, repo_path: Path) -> dict[str, str]:
        versions: dict[str, str] = {}

        # Node version from .nvmrc, .node-version, or package.json engines
        for nvm_file in [".nvmrc", ".node-version"]:
            path = repo_path / nvm_file
            if path.exists():
                content = self.read_file(path)
                if content:
                    versions["node"] = content.strip().lstrip("v")
                    break

        pkg_json = repo_path / "package.json"
        if pkg_json.exists() and "node" not in versions:
            data = self.read_json(pkg_json)
            if data and "engines" in data:
                node_ver = data["engines"].get("node")
                if node_ver:
                    versions["node"] = self._normalize_version(node_ver)

        # Python version from .python-version, pyproject.toml, runtime.txt
        py_ver_file = repo_path / ".python-version"
        if py_ver_file.exists():
            content = self.read_file(py_ver_file)
            if content:
                versions["python"] = content.strip()

        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists() and "python" not in versions:
            content = self.read_file(pyproject)
            if content:
                match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
                if match:
                    versions["python"] = self._normalize_version(match.group(1))

        # Java version from pom.xml or build.gradle
        pom = repo_path / "pom.xml"
        if pom.exists():
            content = self.read_file(pom)
            if content:
                match = re.search(r"<java\.version>([^<]+)</java\.version>", content)
                if match:
                    versions["java"] = match.group(1)

        # .NET version from *.csproj
        for csproj in self.find_files(repo_path, "*.csproj"):
            content = self.read_file(csproj)
            if content:
                match = re.search(r"<TargetFramework>([^<]+)</TargetFramework>", content)
                if match:
                    versions["dotnet"] = match.group(1)
                    break

        return versions


register(TechStackAnalyzer())
