from __future__ import annotations

"""Tests for TechStackAnalyzer."""
import json
from pathlib import Path

from product_builders.analyzers.tech_stack import TechStackAnalyzer


def test_detects_languages_from_files(tmp_path: Path) -> None:
    """Create .ts and .py files outside excluded dirs and assert language percentages."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.ts").write_text("console.log('hello');")
    (src / "utils.ts").write_text("export const foo = 1;")
    (src / "main.py").write_text("print('hi')")

    analyzer = TechStackAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.status.value == "success"
    assert "TypeScript" in result.languages
    assert "Python" in result.languages
    # 2 TS files out of 3 total -> ~66.7%, 1 PY -> ~33.3%
    assert result.languages["TypeScript"] > result.languages["Python"]
    assert result.primary_language == "TypeScript"


def test_detects_frameworks_from_package_json(tmp_path: Path) -> None:
    pkg = {
        "dependencies": {
            "next": "14.0.0",
            "react": "^18.2.0",
        }
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    analyzer = TechStackAnalyzer()
    result = analyzer.analyze(tmp_path)

    fw_names = [fw.name for fw in result.frameworks]
    assert "next" in fw_names
    assert "react" in fw_names


def test_detects_build_tools(tmp_path: Path) -> None:
    (tmp_path / "vite.config.ts").write_text("export default {}")

    analyzer = TechStackAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert "vite" in result.build_tools


def test_detects_package_managers_from_lockfile(tmp_path: Path) -> None:
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: 5.4")

    analyzer = TechStackAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert "pnpm" in result.package_managers


def test_detects_runtime_versions(tmp_path: Path) -> None:
    (tmp_path / ".nvmrc").write_text("20.11.0\n")

    analyzer = TechStackAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.runtime_versions.get("node") == "20.11.0"


def test_empty_repo_returns_success(tmp_path: Path) -> None:
    analyzer = TechStackAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.status.value == "success"
    assert result.languages == {}
    assert result.primary_language is None


def test_normalizes_framework_versions(tmp_path: Path) -> None:
    """Framework version '^18.0.0' should be normalized to '18.0.0'."""
    pkg = {
        "dependencies": {
            "react": "^18.0.0",
        }
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    analyzer = TechStackAnalyzer()
    result = analyzer.analyze(tmp_path)

    react_fw = [fw for fw in result.frameworks if fw.name == "react"]
    assert len(react_fw) == 1
    assert react_fw[0].version == "18.0.0"


def test_excludes_test_dirs_from_language_percentage(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.ts").write_text("const a = 1;")

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_a.ts").write_text("test('a', () => {});")
    (tests / "test_b.ts").write_text("test('b', () => {});")
    (tests / "test_c.ts").write_text("test('c', () => {});")

    analyzer = TechStackAnalyzer()
    result = analyzer.analyze(tmp_path)

    # Only the 1 file in src/ should be counted
    assert "TypeScript" in result.languages
    assert result.languages["TypeScript"] == 100.0


def test_anti_pattern_no_source_files(tmp_path: Path) -> None:
    analyzer = TechStackAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert any("no source code files" in ap for ap in result.anti_patterns)


def test_anti_pattern_no_framework(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("print('hello')")

    analyzer = TechStackAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert any("no framework detected" in ap for ap in result.anti_patterns)
