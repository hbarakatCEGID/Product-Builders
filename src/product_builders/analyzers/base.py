"""Base class for all heuristic analyzers.

Each analyzer examines one dimension of a product codebase (e.g. tech stack,
database patterns, auth) and produces an AnalysisResult subclass.

Analyzers are designed to be:
  - Fully offline (no network, no LLM APIs)
  - Fault-tolerant (partial results on error, never crash the pipeline)
  - Fast (file scanning and pattern matching, not full parsing)
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from product_builders.ast.index import CodebaseIndex

from product_builders.analyzers.deps import (
    LANG_CSHARP,
    LANG_GO,
    LANG_JAVA,
    LANG_JAVASCRIPT,
    LANG_PYTHON,
    LANG_RUBY,
    LANG_RUST,
)
from product_builders.models.analysis import AnalysisResult, AnalysisStatus

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=AnalysisResult)

SKIP_DIRS: frozenset[str] = frozenset({
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".next", ".nuxt", "out", "target", "bin", "obj", ".gradle",
    "vendor", "coverage", ".turbo", ".nx", ".cache",
})

# Cost caps for repository scans (files successfully read with content)
MAX_SOURCE_FILES_AUTH_PERMISSION = 30
MAX_SOURCE_FILES_AUTH_PROTECTED = 20
MAX_SOURCE_FILES_ERROR_HANDLING = 30


class BaseAnalyzer(ABC):
    """Abstract base class for heuristic analyzers.

    Subclasses must implement:
      - name: human-readable analyzer name
      - dimension: which ProductProfile field this populates
      - analyze(repo_path) -> AnalysisResult subclass
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name (e.g. 'Tech Stack Analyzer')."""

    @property
    @abstractmethod
    def dimension(self) -> str:
        """ProductProfile field name this analyzer populates (e.g. 'tech_stack')."""

    @abstractmethod
    def analyze(self, repo_path: Path, *, index: CodebaseIndex | None = None) -> AnalysisResult:
        """Run heuristic analysis on the repository.

        Must return an AnalysisResult subclass (never raise).
        On error, return a result with status=ERROR and error_message set.
        """

    def safe_analyze(self, repo_path: Path, *, index: CodebaseIndex | None = None) -> AnalysisResult:
        """Run analyze() with error handling — never raises."""
        try:
            logger.info("Running %s on %s", self.name, repo_path)
            result = self.analyze(repo_path, index=index)
            logger.info("%s completed: %s", self.name, result.status)
            return result
        except Exception as e:
            logger.error("%s failed: %s", self.name, e, exc_info=True)
            return AnalysisResult(
                status=AnalysisStatus.ERROR,
                error_message=f"{self.name} failed: {e}",
            )

    # ---- Utility methods for subclasses ----

    @staticmethod
    def _normalize_version(raw: str) -> str:
        """Strip semver constraint prefixes: ``'^18.0.0'`` -> ``'18.0.0'``."""
        if not raw:
            return raw
        return re.sub(r"^[~^>=<!\s]+", "", raw).strip()

    def find_files(self, repo_path: Path, *patterns: str) -> list[Path]:
        """Find files matching glob patterns relative to the repo root."""
        matches: list[Path] = []
        for pattern in patterns:
            matches.extend(repo_path.glob(pattern))
        return sorted(set(matches))

    def file_exists(self, repo_path: Path, *relative_paths: str) -> str | None:
        """Return the first relative path that exists, or None."""
        for rel in relative_paths:
            if (repo_path / rel).exists():
                return rel
        return None

    def read_file(self, path: Path, max_bytes: int = 1_000_000) -> str | None:
        """Read a file safely, returning None on error."""
        try:
            st = path.stat()
            if st.st_size > max_bytes:
                logger.warning("Skipping large file: %s (%d bytes)", path, st.st_size)
                return None
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            logger.debug("Could not read file: %s", path, exc_info=True)
            return None

    def read_json(self, path: Path) -> dict | None:
        """Read and parse a JSON file, returning None on error."""
        import json

        content = self.read_file(path)
        if content is None:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    def read_yaml(self, path: Path) -> dict | None:
        """Read and parse a YAML file, returning None on error."""
        import yaml

        content = self.read_file(path)
        if content is None:
            return None
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError:
            return None

    def _get_scan_root(self, repo_path: Path) -> Path:
        """Prefer ``src/`` when present, else repository root."""
        src = repo_path / "src"
        return src if src.is_dir() else repo_path

    def _iter_source_files(
        self,
        repo_path: Path,
        *,
        extensions: frozenset[str],
        max_files: int,
    ) -> Iterator[tuple[Path, str]]:
        """Walk scan root, yielding up to ``max_files`` paths with non-empty file content."""
        scan_dir = self._get_scan_root(repo_path)
        count = 0
        for path in scan_dir.rglob("*"):
            if count >= max_files:
                break
            if not path.is_file() or any(s in path.parts for s in SKIP_DIRS):
                continue
            if path.suffix not in extensions:
                continue
            content = self.read_file(path)
            if not content:
                continue
            count += 1
            yield path, content

    def _detect_primary_language(self, repo_path: Path) -> str | None:
        """Infer the primary language from manifest files present in the repo."""
        if (repo_path / "package.json").exists():
            return LANG_JAVASCRIPT
        if (repo_path / "pyproject.toml").exists() or (repo_path / "setup.py").exists():
            return LANG_PYTHON
        if (repo_path / "pom.xml").exists() or (repo_path / "build.gradle").exists():
            return LANG_JAVA
        if any((repo_path / f).exists() for f in ("Gemfile", "Rakefile")):
            return LANG_RUBY
        if (repo_path / "go.mod").exists():
            return LANG_GO
        if (repo_path / "Cargo.toml").exists():
            return LANG_RUST
        if any(self.find_files(repo_path, "*.csproj")):
            return LANG_CSHARP
        return None

    def _collect_dep_names(
        self, repo_path: Path, *, include_requirements_txt: bool = True
    ) -> set[str]:
        """Dependency names from common manifests (npm, Python, JVM, .NET, Ruby)."""
        deps: set[str] = set()

        pkg_json = repo_path / "package.json"
        if pkg_json.exists():
            data = self.read_json(pkg_json)
            if data:
                for section in ("dependencies", "devDependencies"):
                    deps.update(data.get(section, {}).keys())

        if include_requirements_txt:
            for req_file in self.find_files(repo_path, "requirements*.txt"):
                content = self.read_file(req_file)
                if content:
                    for line in content.splitlines():
                        line = line.strip()
                        if line and not line.startswith(("#", "-")):
                            name = re.split(r"[><=!~\[]", line)[0].strip()
                            if name:
                                deps.add(name)

        pom = repo_path / "pom.xml"
        if pom.exists():
            content = self.read_file(pom)
            if content:
                for m in re.finditer(r"<artifactId>([^<]+)</artifactId>", content):
                    deps.add(m.group(1))

        for csproj in self.find_files(repo_path, "*.csproj"):
            content = self.read_file(csproj)
            if content:
                for m in re.finditer(r'Include="([^"]+)"', content):
                    deps.add(m.group(1))

        gemfile = repo_path / "Gemfile"
        if gemfile.exists():
            content = self.read_file(gemfile)
            if content:
                for m in re.finditer(r"gem\s+['\"]([^'\"]+)['\"]", content):
                    deps.add(m.group(1))

        return deps

    def collect_dependency_names(
        self,
        repo_path: Path,
        *,
        include_requirements_txt: bool = True,
        pyproject_substrings: frozenset[str] | None = None,
    ) -> set[str]:
        """Union of manifest deps plus optional ``pyproject.toml`` substring hints.

        ``pyproject_substrings``: if a substring appears anywhere in ``pyproject.toml``,
        that substring is added to the set (offline heuristic for unpinned tools).
        """
        deps = self._collect_dep_names(
            repo_path, include_requirements_txt=include_requirements_txt
        )
        if pyproject_substrings:
            pyproject = repo_path / "pyproject.toml"
            if pyproject.exists():
                content = self.read_file(pyproject)
                if content:
                    for s in pyproject_substrings:
                        if s in content:
                            deps.add(s)
        return deps
