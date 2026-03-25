"""Merge user-provided overrides into a ProductProfile."""
from __future__ import annotations

import logging

from product_builders.models.profile import ProductProfile

logger = logging.getLogger(__name__)


def merge_overrides(
    profile: ProductProfile, overrides: dict[str, dict]
) -> ProductProfile:
    """Return a new profile with override values merged in.

    Only known dimension names are accepted.  Within each dimension the
    override dict is shallow-merged — override keys win, unmentioned keys
    are preserved from the original.  Setting a key to ``None`` in the
    override erases the heuristic value (intentional).

    Unknown dimension names are logged and skipped.
    """
    if not overrides:
        return profile

    data = profile.model_dump()
    for dimension, values in overrides.items():
        if dimension not in data:
            logger.warning("Override key %r does not match any profile dimension, ignoring", dimension)
            continue
        if isinstance(values, dict) and isinstance(data[dimension], dict):
            data[dimension].update(values)
    return ProductProfile.model_validate(data)
