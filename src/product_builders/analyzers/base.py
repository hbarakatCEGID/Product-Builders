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
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeVar

from product_builders.models.analysis import AnalysisResult, AnalysisStatus

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=AnalysisResult)

SKIP_DIRS: frozenset[str] = frozenset({
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".next", ".nuxt", "out", "target", "bin", "obj", ".gradle",
    "vendor", "coverage", ".turbo", ".nx", ".cache",
})


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
    def analyze(self, repo_path: Path) -> AnalysisResult:
        """Run heuristic analysis on the repository.

        Must return an AnalysisResult subclass (never raise).
        On error, return a result with status=ERROR and error_message set.
        """

    def safe_analyze(self, repo_path: Path) -> AnalysisResult:
        """Run analyze() with error handling — never raises."""
        try:
            logger.info("Running %s on %s", self.name, repo_path)
            result = self.analyze(repo_path)
            logger.info("%s completed: %s", self.name, result.status)
            return result
        except Exception as e:
            logger.error("%s failed: %s", self.name, e, exc_info=True)
            return AnalysisResult(
                status=AnalysisStatus.ERROR,
                error_message=f"{self.name} failed: {e}",
            )

    # ---- Utility methods for subclasses ----

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
