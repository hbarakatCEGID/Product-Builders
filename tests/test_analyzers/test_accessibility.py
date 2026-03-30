from __future__ import annotations

"""Tests for AccessibilityAnalyzer."""
import json
from pathlib import Path

from product_builders.analyzers.accessibility import AccessibilityAnalyzer


def test_detects_axe_core_tool(tmp_path: Path) -> None:
    """package.json with axe-core, assert 'axe-core' in a11y_testing_tools."""
    pkg = {"devDependencies": {"axe-core": "^4.7.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = AccessibilityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert "axe-core" in result.a11y_testing_tools


def test_detects_jest_axe_tool(tmp_path: Path) -> None:
    """package.json with jest-axe, assert 'jest-axe' in a11y_testing_tools."""
    pkg = {"devDependencies": {"jest-axe": "^8.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = AccessibilityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert "jest-axe" in result.a11y_testing_tools


def test_detects_aria_usage(tmp_path: Path) -> None:
    """Create src/Button.tsx with aria-label, assert aria_usage_detected is True."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "Button.tsx").write_text(
        'export const Button = () => <button aria-label="close">X</button>;'
    )
    analyzer = AccessibilityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.aria_usage_detected is True


def test_detects_high_semantic_html(tmp_path: Path) -> None:
    """Create files with many semantic tags vs few divs, assert semantic_html_score == 'high'."""
    src = tmp_path / "src"
    src.mkdir()
    # Many semantic tags, few divs -> ratio > 0.3 -> "high"
    content = (
        "<nav>Nav</nav>\n"
        "<main>Main content</main>\n"
        "<article>Article</article>\n"
        "<section>Section</section>\n"
        "<header>Header</header>\n"
        "<footer>Footer</footer>\n"
        "<aside>Sidebar</aside>\n"
        "<div>One div</div>\n"
    )
    (src / "Layout.tsx").write_text(content)
    analyzer = AccessibilityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.semantic_html_score == "high"


def test_detects_keyboard_navigation(tmp_path: Path) -> None:
    """Create file with onKeyDown handler, assert keyboard_navigation is True."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "Search.tsx").write_text(
        'export const Search = () => <input onKeyDown={(e) => handleKey(e)} />;'
    )
    analyzer = AccessibilityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.keyboard_navigation is True


def test_empty_repo(tmp_path: Path) -> None:
    """Empty repo, assert a11y_testing_tools is empty."""
    analyzer = AccessibilityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.a11y_testing_tools == []


def test_anti_pattern_no_a11y_tools(tmp_path: Path) -> None:
    """No a11y tools, should trigger anti-pattern."""
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"react": "^18.0.0"}}))
    analyzer = AccessibilityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("no accessibility testing tools" in ap.lower() for ap in result.anti_patterns)


def test_anti_pattern_no_aria(tmp_path: Path) -> None:
    """Source files but no ARIA attributes, should trigger anti-pattern."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "App.tsx").write_text(
        "export const App = () => <div><span>Hello</span></div>;"
    )
    analyzer = AccessibilityAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("no aria" in ap.lower() for ap in result.anti_patterns)
