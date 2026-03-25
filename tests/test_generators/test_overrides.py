"""Tests for overrides.yaml merging into ProductProfile."""
from product_builders.models.profile import ProductProfile, ProductMetadata
from product_builders.models.analysis import DatabaseResult
from product_builders.profiles.overrides import merge_overrides


def test_override_database_type() -> None:
    """overrides.yaml should be able to set database_type."""
    profile = ProductProfile(
        metadata=ProductMetadata(name="test"),
        database=DatabaseResult(database_type=None),
    )
    overrides = {"database": {"database_type": "postgresql"}}
    updated = merge_overrides(profile, overrides)
    assert updated.database.database_type == "postgresql"


def test_override_preserves_existing_values() -> None:
    """Overrides should not wipe fields that aren't overridden."""
    profile = ProductProfile(
        metadata=ProductMetadata(name="test"),
        database=DatabaseResult(database_type="mysql", orm="prisma"),
    )
    overrides = {"database": {"database_type": "postgresql"}}
    updated = merge_overrides(profile, overrides)
    assert updated.database.database_type == "postgresql"
    assert updated.database.orm == "prisma"


def test_empty_overrides_returns_unchanged() -> None:
    """Empty overrides dict should return profile unchanged."""
    profile = ProductProfile(metadata=ProductMetadata(name="test"))
    updated = merge_overrides(profile, {})
    assert updated.model_dump() == profile.model_dump()
