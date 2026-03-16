"""Analyzer registry — central place to register and retrieve all analyzers.

New analyzers are registered here as they are implemented across Phases 2-4.
"""

from __future__ import annotations

import importlib
import logging

from product_builders.analyzers.base import BaseAnalyzer

logger = logging.getLogger(__name__)

_ANALYZERS: list[BaseAnalyzer] = []


def register(analyzer: BaseAnalyzer) -> BaseAnalyzer:
    """Register an analyzer instance (deduplicates by dimension)."""
    if any(a.dimension == analyzer.dimension for a in _ANALYZERS):
        return analyzer
    _ANALYZERS.append(analyzer)
    return analyzer


def get_all_analyzers() -> list[BaseAnalyzer]:
    """Return all registered analyzer instances, ordered by registration."""
    return list(_ANALYZERS)


def get_analyzer(dimension: str) -> BaseAnalyzer | None:
    """Return the analyzer for a specific dimension, or None."""
    return next((a for a in _ANALYZERS if a.dimension == dimension), None)


# ---------------------------------------------------------------------------
# Auto-register analyzers as they are implemented.
# Uses ModuleNotFoundError (not ImportError) to avoid silencing real bugs
# inside existing modules.
# ---------------------------------------------------------------------------
_ANALYZER_MODULES = [
    "tech_stack", "structure", "dependencies", "conventions",
    "database", "auth", "error_handling", "git_workflow",
]

for _mod_name in _ANALYZER_MODULES:
    try:
        importlib.import_module(f"product_builders.analyzers.{_mod_name}")
    except ModuleNotFoundError:
        pass
    except Exception:
        logger.warning("Failed to load analyzer module '%s'", _mod_name, exc_info=True)
