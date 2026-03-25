from __future__ import annotations

"""Tests for zone auto-detection and scope generation."""
from pathlib import Path
from product_builders.generators.scopes import auto_detect_zones


def test_detects_api_zone_under_src(tmp_path: Path) -> None:
    """src/app/api/ should be detected as 'api' zone."""
    (tmp_path / "src" / "app" / "api").mkdir(parents=True)
    zones = auto_detect_zones(tmp_path)
    zone_names = [z.name for z in zones]
    assert "api" in zone_names


def test_detects_tests_zone_nested(tmp_path: Path) -> None:
    """Nested __tests__/ dirs should be detected as 'tests' zone."""
    (tmp_path / "src" / "lib" / "__tests__").mkdir(parents=True)
    zones = auto_detect_zones(tmp_path)
    zone_names = [z.name for z in zones]
    assert "tests" in zone_names


def test_detects_database_zone_nested(tmp_path: Path) -> None:
    """supabase/migrations/ should be detected as 'database' zone."""
    (tmp_path / "supabase" / "migrations").mkdir(parents=True)
    zones = auto_detect_zones(tmp_path)
    zone_names = [z.name for z in zones]
    assert "database" in zone_names


def test_detects_direct_pattern(tmp_path: Path) -> None:
    """Direct pattern like tests/ at root should still work."""
    (tmp_path / "tests").mkdir()
    zones = auto_detect_zones(tmp_path)
    zone_names = [z.name for z in zones]
    assert "tests" in zone_names


def test_no_duplicate_zones(tmp_path: Path) -> None:
    """Multiple matching patterns for same zone should not duplicate."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "__tests__").mkdir(parents=True)
    zones = auto_detect_zones(tmp_path)
    zone_names = [z.name for z in zones]
    assert zone_names.count("tests") == 1
