from __future__ import annotations

"""Tests for database analyzer BaaS detection."""
import json
from pathlib import Path
from product_builders.analyzers.database import DatabaseAnalyzer


def test_detects_supabase_as_postgresql(tmp_path: Path) -> None:
    """Supabase JS client should map to postgresql database type."""
    pkg = {"dependencies": {"@supabase/supabase-js": "^2.99.1"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = DatabaseAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.database_type == "postgresql"


def test_detects_firebase_as_firebase(tmp_path: Path) -> None:
    """Firebase should map to firebase database type."""
    pkg = {"dependencies": {"firebase": "^10.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = DatabaseAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.database_type == "firebase"


def test_detects_planetscale_as_mysql(tmp_path: Path) -> None:
    """PlanetScale client should map to mysql."""
    pkg = {"dependencies": {"@planetscale/database": "^1.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = DatabaseAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.database_type == "mysql"
