"""Merge user-provided overrides into a ProductProfile."""
from __future__ import annotations

from product_builders.models.profile import ProductProfile


def merge_overrides(
    profile: ProductProfile, overrides: dict
) -> ProductProfile:
    """Return a new profile with override values merged in.

    Only known dimension names are accepted.  Within each dimension the
    override dict is shallow-merged (override keys win, unmentioned keys
    are preserved from the original).
    """
    if not overrides:
        return profile

    data = profile.model_dump()
    for dimension, values in overrides.items():
        if dimension in data and isinstance(values, dict) and isinstance(data[dimension], dict):
            data[dimension].update(values)
    return ProductProfile.model_validate(data)
