"""Project Structure Analyzer — Dimension 10 (MEDIUM IMPACT).

Detects directory organization patterns, module layout, monorepo markers,
and identifies key directories and their purposes.
"""

from __future__ import annotations

from pathlib import Path

from product_builders.analyzers.base import SKIP_DIRS, BaseAnalyzer
from product_builders.analyzers.registry import register
from product_builders.models.analysis import (
    AnalysisStatus,
    DirectoryPattern,
    StructureResult,
)

MONOREPO_MARKERS: dict[str, str] = {
    "lerna.json": "lerna",
    "pnpm-workspace.yaml": "pnpm-workspaces",
    "nx.json": "nx",
    "turbo.json": "turborepo",
    "rush.json": "rush",
    ".moon/workspace.yml": "moon",
}

KNOWN_DIRECTORY_PURPOSES: dict[str, str] = {
    "src": "Source code",
    "lib": "Library code",
    "app": "Application code",
    "apps": "Multiple applications (monorepo)",
    "packages": "Shared packages (monorepo)",
    "components": "UI components",
    "pages": "Page components / routes",
    "views": "View components / templates",
    "api": "API endpoints",
    "routes": "Route definitions",
    "controllers": "Request handlers",
    "services": "Business logic services",
    "models": "Data models / entities",
    "schemas": "Schema definitions",
    "migrations": "Database migrations",
    "prisma": "Prisma ORM config and schema",
    "tests": "Test files",
    "test": "Test files",
    "__tests__": "Test files (Jest convention)",
    "spec": "Test specifications",
    "fixtures": "Test fixtures / seed data",
    "config": "Configuration files",
    "public": "Static public assets",
    "static": "Static files",
    "assets": "Media and asset files",
    "styles": "Stylesheets",
    "css": "CSS files",
    "hooks": "React hooks / lifecycle hooks",
    "utils": "Utility functions",
    "helpers": "Helper functions",
    "middleware": "Middleware layers",
    "plugins": "Plugin modules",
    "types": "TypeScript type definitions",
    "interfaces": "Interface definitions",
    "locales": "Translation files",
    "i18n": "Internationalization",
    "docs": "Documentation",
    "scripts": "Build / utility scripts",
    "tools": "Development tools",
    ".github": "GitHub config (actions, templates)",
    ".gitlab": "GitLab config",
    ".vscode": "VS Code settings",
    ".cursor": "Cursor IDE settings",
    "docker": "Docker configuration",
    "deploy": "Deployment configuration",
    "infra": "Infrastructure as code",
    "terraform": "Terraform config",
    "k8s": "Kubernetes manifests",
    "store": "State store",
    "redux": "Redux store",
    "auth": "Authentication module",
    "guards": "Route / permission guards",
    "entities": "Domain entities",
    "widgets": "Widget components",
    "features": "Feature modules",
    "shared": "Shared utilities and components",
}

ORGANIZATION_PATTERNS: list[tuple[str, list[str]]] = [
    ("feature-based", ["features/", "modules/"]),
    ("layered", ["controllers/", "services/", "models/", "repositories/"]),
    ("domain-driven", ["domain/", "application/", "infrastructure/"]),
    ("flat", []),
]


class StructureAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Project Structure Analyzer"

    @property
    def dimension(self) -> str:
        return "structure"

    def analyze(self, repo_path: Path, *, index=None) -> StructureResult:
        root_dirs = self._get_root_directories(repo_path)
        source_dirs = self._find_source_directories(repo_path)
        key_dirs = self._identify_key_directories(repo_path)
        org_pattern = self._detect_organization(repo_path)
        is_mono, mono_tool, sub_projects = self._detect_monorepo(repo_path)

        result = StructureResult(
            status=AnalysisStatus.SUCCESS,
            root_directories=root_dirs,
            source_directories=source_dirs,
            key_directories=key_dirs,
            module_organization=org_pattern,
            is_monorepo=is_mono,
            monorepo_tool=mono_tool,
            sub_projects=sub_projects,
        )

        anti_patterns = []
        if result.is_monorepo and not result.monorepo_tool:
            anti_patterns.append("MEDIUM: monorepo structure but no monorepo tooling (Turborepo, Nx, etc.)")
        if not result.source_directories:
            anti_patterns.append("MEDIUM: no standard source directory (src/, lib/, app/) — project layout may be unclear")
        if result.module_organization == "flat":
            anti_patterns.append("LOW: flat module organization — consider feature-based or layered structure for scaling")
        result.anti_patterns = anti_patterns

        return result

    def _get_root_directories(self, repo_path: Path) -> list[str]:
        return sorted(
            d.name for d in repo_path.iterdir()
            if d.is_dir() and d.name not in SKIP_DIRS and not d.name.startswith(".")
        )

    def _find_source_directories(self, repo_path: Path) -> list[str]:
        candidates = ["src", "lib", "app", "source"]
        return [d for d in candidates if (repo_path / d).is_dir()]

    def _identify_key_directories(self, repo_path: Path) -> list[DirectoryPattern]:
        patterns: list[DirectoryPattern] = []

        def _scan(base: Path, depth: int = 0, prefix: str = "") -> None:
            if depth > 3:
                return
            try:
                entries = sorted(base.iterdir())
            except PermissionError:
                return
            for entry in entries:
                if not entry.is_dir() or entry.name in SKIP_DIRS or entry.name.startswith("."):
                    continue
                rel = f"{prefix}{entry.name}" if prefix else entry.name
                purpose = KNOWN_DIRECTORY_PURPOSES.get(entry.name, "")
                if purpose:
                    patterns.append(DirectoryPattern(path=rel, purpose=purpose))
                _scan(entry, depth + 1, f"{rel}/")

        _scan(repo_path)
        return patterns

    def _detect_organization(self, repo_path: Path) -> str | None:
        src = repo_path / "src"
        scan_root = src if src.is_dir() else repo_path

        dir_names = set()
        try:
            for entry in scan_root.iterdir():
                if entry.is_dir() and entry.name not in SKIP_DIRS:
                    dir_names.add(entry.name)
                    for sub in entry.iterdir():
                        if sub.is_dir():
                            dir_names.add(f"{entry.name}/{sub.name}")
        except PermissionError:
            pass

        for pattern_name, markers in ORGANIZATION_PATTERNS:
            if markers and all(any(m.rstrip("/") in d for d in dir_names) for m in markers):
                return pattern_name

        return "flat"

    def _detect_monorepo(self, repo_path: Path) -> tuple[bool, str | None, list[str]]:
        mono_tool = None
        for marker_file, tool_name in MONOREPO_MARKERS.items():
            if (repo_path / marker_file).exists():
                mono_tool = tool_name
                break

        sub_projects: list[str] = []
        for candidate_dir in ["apps", "packages", "services", "libs", "modules"]:
            base = repo_path / candidate_dir
            if base.is_dir():
                for child in sorted(base.iterdir()):
                    if child.is_dir() and not child.name.startswith("."):
                        has_manifest = any(
                            (child / f).exists()
                            for f in ["package.json", "pyproject.toml", "pom.xml", "build.gradle", "Cargo.toml"]
                        )
                        if has_manifest:
                            sub_projects.append(str(child.relative_to(repo_path)))

        is_monorepo = mono_tool is not None or len(sub_projects) > 1
        return is_monorepo, mono_tool, sub_projects


register(StructureAnalyzer())
