from __future__ import annotations

"""Tests for design analyzer component library detection."""
import json
from pathlib import Path
from product_builders.analyzers.design import DesignUIAnalyzer


def test_detects_shadcn(tmp_path: Path) -> None:
    """shadcn package should be detected as component library."""
    pkg = {"dependencies": {"shadcn": "^4.0.5"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = DesignUIAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.component_library == "shadcn"


def test_detects_shadcn_ui(tmp_path: Path) -> None:
    """@shadcn/ui should also be detected."""
    pkg = {"dependencies": {"@shadcn/ui": "^1.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = DesignUIAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.component_library == "shadcn"
