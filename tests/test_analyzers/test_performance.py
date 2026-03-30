from __future__ import annotations

"""Tests for PerformanceAnalyzer."""
import json
from pathlib import Path

from product_builders.analyzers.performance import PerformanceAnalyzer


def test_detects_redis_caching(tmp_path: Path) -> None:
    pkg = {"dependencies": {"redis": "^4.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.caching_strategy == "redis"


def test_detects_lazy_loading(tmp_path: Path) -> None:
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
    pkg = {"dependencies": {"sharp": "^0.32.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.image_optimization == "sharp"


def test_detects_sentry_monitoring(tmp_path: Path) -> None:
    pkg = {"dependencies": {"@sentry/node": "^7.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.performance_monitoring == "sentry"


def test_detects_service_worker(tmp_path: Path) -> None:
    public = tmp_path / "public"
    public.mkdir()
    (public / "sw.js").write_text(
        "self.addEventListener('install', (event) => { console.log('SW installed'); });\n"
    )
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.service_worker_detected is True


def test_empty_repo(tmp_path: Path) -> None:
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.caching_strategy is None


def test_anti_pattern_no_monitoring(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"react": "^18.0.0"}}))
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("no web performance monitoring" in ap.lower() for ap in result.anti_patterns)


def test_anti_pattern_no_lazy_loading(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "App.tsx").write_text(
        "import Page from './Page';\n"
        "export default function App() { return <Page />; }\n"
    )
    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("no lazy loading" in ap.lower() for ap in result.anti_patterns)
