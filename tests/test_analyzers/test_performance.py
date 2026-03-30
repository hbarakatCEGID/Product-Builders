from __future__ import annotations

"""Tests for PerformanceAnalyzer."""
import json
from pathlib import Path

from product_builders.analyzers.performance import PerformanceAnalyzer


def test_detects_redis_caching(tmp_path: Path) -> None:
    """package.json with redis, assert caching_strategy == 'redis'."""
    pkg = {"dependencies": {"redis": "^4.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.caching_strategy == "redis"


def test_detects_lazy_loading(tmp_path: Path) -> None:
    """Create src/App.tsx with React.lazy, assert lazy_loading is True."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "App.tsx").write_text(
        "import React from 'react';\n"
        "const LazyPage = React.lazy(() => import('./Page'));\n"
        "export default function App() { return <LazyPage />; }\n"
    )
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.lazy_loading is True


def test_detects_code_splitting(tmp_path: Path) -> None:
    """Create src/App.tsx with dynamic import(), assert code_splitting is True."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "App.tsx").write_text(
        "import React from 'react';\n"
        "const LazyPage = React.lazy(() => import(/* webpackChunkName: 'page' */ './Page'));\n"
        "export default function App() { return <LazyPage />; }\n"
    )
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.code_splitting is True


def test_detects_sharp_image_optimization(tmp_path: Path) -> None:
    """package.json with sharp, assert image_optimization == 'sharp'."""
    pkg = {"dependencies": {"sharp": "^0.32.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.image_optimization == "sharp"


def test_detects_sentry_monitoring(tmp_path: Path) -> None:
    """package.json with @sentry/node, assert performance_monitoring is set."""
    pkg = {"dependencies": {"@sentry/node": "^7.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.performance_monitoring == "sentry"


def test_detects_service_worker(tmp_path: Path) -> None:
    """Create public/sw.js, assert service_worker_detected is True."""
    public = tmp_path / "public"
    public.mkdir()
    (public / "sw.js").write_text(
        "self.addEventListener('install', (event) => { console.log('SW installed'); });\n"
    )
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.service_worker_detected is True


def test_empty_repo(tmp_path: Path) -> None:
    """Empty repo, assert caching_strategy is None."""
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.caching_strategy is None


def test_anti_pattern_no_monitoring(tmp_path: Path) -> None:
    """No monitoring tool, should trigger anti-pattern about web performance monitoring."""
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"react": "^18.0.0"}}))
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("no web performance monitoring" in ap.lower() for ap in result.anti_patterns)


def test_anti_pattern_no_lazy_loading(tmp_path: Path) -> None:
    """Source files but no lazy loading, should trigger anti-pattern."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "App.tsx").write_text(
        "import Page from './Page';\n"
        "export default function App() { return <Page />; }\n"
    )
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("no lazy loading" in ap.lower() for ap in result.anti_patterns)
