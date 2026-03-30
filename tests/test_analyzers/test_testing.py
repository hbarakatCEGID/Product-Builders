from __future__ import annotations

"""Tests for testing analyzer."""
import json
from pathlib import Path

from product_builders.analyzers.testing import TestingAnalyzer


def test_detects_jest_framework(tmp_path: Path) -> None:
    (tmp_path / "jest.config.js").write_text("module.exports = { testEnvironment: 'node' };")
    analyzer = TestingAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.test_framework == "jest"


def test_detects_vitest_framework(tmp_path: Path) -> None:
    (tmp_path / "vitest.config.ts").write_text("import { defineConfig } from 'vitest/config';\nexport default defineConfig({});")
    analyzer = TestingAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.test_framework == "vitest"


def test_detects_pytest_framework(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests")
    analyzer = TestingAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.test_framework == "pytest"


def test_detects_pytest_via_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.pytest.ini_options]\ntestpaths = ["tests"]')
    analyzer = TestingAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.test_framework == "pytest"


def test_detects_test_directories(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    analyzer = TestingAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert "tests" in result.test_directories


def test_detects_cypress_e2e(tmp_path: Path) -> None:
    pkg = {"devDependencies": {"cypress": "^13.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = TestingAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.e2e_framework == "cypress"


def test_detects_playwright_e2e(tmp_path: Path) -> None:
    pkg = {"devDependencies": {"@playwright/test": "^1.40.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = TestingAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.e2e_framework == "playwright"


def test_detects_coverage_tool(tmp_path: Path) -> None:
    pkg = {"devDependencies": {"c8": "^8.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = TestingAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.coverage_tool == "c8"


def test_detects_msw_mocking(tmp_path: Path) -> None:
    pkg = {"devDependencies": {"msw": "^2.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = TestingAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.mocking_library == "msw"


def test_empty_repo_no_tests(tmp_path: Path) -> None:
    analyzer = TestingAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("no tests" in ap.lower() or "no test framework" in ap.lower() for ap in result.anti_patterns)


def test_anti_pattern_no_coverage(tmp_path: Path) -> None:
    (tmp_path / "jest.config.js").write_text("module.exports = {};")
    analyzer = TestingAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("coverage" in ap.lower() for ap in result.anti_patterns)


def test_detects_nested_tests_dirs(tmp_path: Path) -> None:
    nested = tmp_path / "src" / "components" / "__tests__"
    nested.mkdir(parents=True)
    (nested / "Button.test.tsx").write_text("test('renders', () => {});")

    analyzer = TestingAnalyzer()
    result = analyzer.analyze(tmp_path)

    # Should find the nested __tests__ directory
    found_nested = any("__tests__" in d for d in result.test_directories)
    assert found_nested, f"Expected nested __tests__ in {result.test_directories}"
