from __future__ import annotations

"""Tests for FrontendPatternsAnalyzer."""
import json
from pathlib import Path

from product_builders.analyzers.frontend_patterns import FrontendPatternsAnalyzer


def test_detects_react_hook_form(tmp_path: Path) -> None:
    """package.json with react-hook-form, assert 'react-hook-form' in form_libraries."""
    pkg = {"dependencies": {"react-hook-form": "^7.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = FrontendPatternsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert "react-hook-form" in result.form_libraries


def test_detects_react_router(tmp_path: Path) -> None:
    """package.json with react-router-dom, assert routing_library == 'react-router'."""
    pkg = {"dependencies": {"react-router-dom": "^6.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = FrontendPatternsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.routing_library == "react-router"


def test_detects_framer_motion(tmp_path: Path) -> None:
    """package.json with framer-motion, assert animation_library == 'framer-motion'."""
    pkg = {"dependencies": {"framer-motion": "^10.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = FrontendPatternsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.animation_library == "framer-motion"


def test_detects_error_boundary(tmp_path: Path) -> None:
    """Create component with 'ErrorBoundary' text, assert error_boundary is True."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "ErrorBoundary.tsx").write_text(
        "import React from 'react';\n"
        "class ErrorBoundary extends React.Component {\n"
        "  componentDidCatch(error, info) { console.error(error); }\n"
        "  render() { return this.props.children; }\n"
        "}\n"
        "export default ErrorBoundary;\n"
    )
    analyzer = FrontendPatternsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.error_boundary is True


def test_detects_loading_patterns(tmp_path: Path) -> None:
    """Create component with 'Skeleton' text, assert loading_patterns is non-empty."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "Loading.tsx").write_text(
        "export const Loading = () => <Skeleton width={200} height={20} />;\n"
    )
    analyzer = FrontendPatternsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert len(result.loading_patterns) > 0
    assert "skeleton" in result.loading_patterns


def test_detects_react_virtualized(tmp_path: Path) -> None:
    """package.json with react-window, assert list_virtualization == 'react-window'."""
    pkg = {"dependencies": {"react-window": "^1.8.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = FrontendPatternsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.list_virtualization == "react-window"


def test_empty_repo(tmp_path: Path) -> None:
    """Empty repo, assert form_libraries is empty."""
    analyzer = FrontendPatternsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.form_libraries == []


def test_anti_pattern_no_error_boundary(tmp_path: Path) -> None:
    """Source files but no error boundary, should trigger anti-pattern."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "App.tsx").write_text(
        "export const App = () => <div>Hello World</div>;\n"
    )
    analyzer = FrontendPatternsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("no error boundary" in ap.lower() for ap in result.anti_patterns)
