"""Generator registry — central place to register and retrieve all generators.

New generators are registered here as they are implemented in Phase 3.
"""

from __future__ import annotations

import importlib
import logging

from product_builders.generators.base import BaseGenerator

logger = logging.getLogger(__name__)

_GENERATORS: list[BaseGenerator] = []


def register(generator: BaseGenerator) -> BaseGenerator:
    """Register a generator instance (deduplicates by name)."""
    if any(g.name == generator.name for g in _GENERATORS):
        return generator
    _GENERATORS.append(generator)
    return generator


def get_all_generators() -> list[BaseGenerator]:
    """Return all registered generator instances."""
    return list(_GENERATORS)


# ---------------------------------------------------------------------------
# Auto-register generators as they are implemented.
# ---------------------------------------------------------------------------
_GENERATOR_MODULES = [
    "cursor_rules", "cursor_hooks", "cursor_permissions", "onboarding",
    "review_checklist", "enrichment",
]

for _mod_name in _GENERATOR_MODULES:
    try:
        importlib.import_module(f"product_builders.generators.{_mod_name}")
    except ModuleNotFoundError:
        pass
    except (ImportError, SyntaxError, AttributeError) as e:
        logger.warning("Failed to load generator module '%s': %s", _mod_name, e, exc_info=True)
