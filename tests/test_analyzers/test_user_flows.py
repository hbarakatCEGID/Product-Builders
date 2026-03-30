from __future__ import annotations

"""Tests for UserFlowsAnalyzer."""
import json
from pathlib import Path

from product_builders.analyzers.user_flows import UserFlowsAnalyzer


def test_detects_page_routes(tmp_path: Path) -> None:
    pages = tmp_path / "src" / "pages"
    pages.mkdir(parents=True)
    (pages / "index.tsx").write_text("export default function Home() { return <div>Home</div>; }")
    (pages / "about.tsx").write_text("export default function About() { return <div>About</div>; }")
    analyzer = UserFlowsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.route_count >= 2


def test_detects_nextjs_navigation(tmp_path: Path) -> None:
    (tmp_path / "src" / "app").mkdir(parents=True)
    pkg = {"dependencies": {"next": "^14.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = UserFlowsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.navigation_type is not None
    assert "app-router" in result.navigation_type


def test_detects_404_page(tmp_path: Path) -> None:
    pages = tmp_path / "src" / "pages"
    pages.mkdir(parents=True)
    (pages / "index.tsx").write_text("export default function Home() { return <div />; }")
    (pages / "404.tsx").write_text("export default function NotFound() { return <div>404</div>; }")
    analyzer = UserFlowsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.has_404_page is True


def test_detects_error_page(tmp_path: Path) -> None:
    pages = tmp_path / "src" / "pages"
    pages.mkdir(parents=True)
    (pages / "index.tsx").write_text("export default function Home() { return <div />; }")
    (pages / "_error.tsx").write_text("export default function Error() { return <div>Error</div>; }")
    analyzer = UserFlowsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.has_error_page is True


def test_detects_dynamic_routes(tmp_path: Path) -> None:
    pages = tmp_path / "src" / "pages"
    pages.mkdir(parents=True)
    (pages / "index.tsx").write_text("export default function Home() { return <div />; }")
    (pages / "[id].tsx").write_text("export default function Detail() { return <div>Detail</div>; }")
    analyzer = UserFlowsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert len(result.dynamic_routes) > 0


def test_detects_auth_protected_routes(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "routes.tsx").write_text(
        "import { ProtectedRoute } from './auth';\n"
        "export const routes = [\n"
        "  { path: '/dashboard', element: <ProtectedRoute><Dashboard /></ProtectedRoute> },\n"
        "];\n"
    )
    analyzer = UserFlowsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.auth_protected_routes is True


def test_empty_repo(tmp_path: Path) -> None:
    analyzer = UserFlowsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.route_count == 0


def test_anti_pattern_no_404(tmp_path: Path) -> None:
    pages = tmp_path / "src" / "pages"
    pages.mkdir(parents=True)
    (pages / "index.tsx").write_text("export default function Home() { return <div />; }")
    (pages / "about.tsx").write_text("export default function About() { return <div />; }")
    analyzer = UserFlowsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.route_count > 0
    assert any("no 404" in ap.lower() for ap in result.anti_patterns)


def test_anti_pattern_no_error_page(tmp_path: Path) -> None:
    pages = tmp_path / "src" / "pages"
    pages.mkdir(parents=True)
    (pages / "index.tsx").write_text("export default function Home() { return <div />; }")
    (pages / "about.tsx").write_text("export default function About() { return <div />; }")
    analyzer = UserFlowsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.route_count > 0
    assert any("no error page" in ap.lower() for ap in result.anti_patterns)
