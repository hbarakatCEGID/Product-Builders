from __future__ import annotations

"""Tests for ConventionsAnalyzer."""
import json
from pathlib import Path

from product_builders.analyzers.conventions import ConventionsAnalyzer


def test_detects_eslint_linter(tmp_path: Path) -> None:
    """Create .eslintrc.json, assert linter == 'eslint'."""
    (tmp_path / ".eslintrc.json").write_text(json.dumps({"rules": {}}))
    analyzer = ConventionsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.linter == "eslint"


def test_detects_ruff_linter(tmp_path: Path) -> None:
    """Create pyproject.toml with [tool.ruff], assert linter == 'ruff'."""
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
    analyzer = ConventionsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.linter == "ruff"


def test_detects_prettier_formatter(tmp_path: Path) -> None:
    """Create .prettierrc, assert formatter == 'prettier'."""
    (tmp_path / ".prettierrc").write_text(json.dumps({"semi": True}))
    analyzer = ConventionsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.formatter == "prettier"


def test_detects_biome_formatter(tmp_path: Path) -> None:
    """Create biome.json, assert formatter == 'biome'."""
    (tmp_path / "biome.json").write_text(json.dumps({"formatter": {"enabled": True}}))
    analyzer = ConventionsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.formatter == "biome"


def test_detects_editorconfig(tmp_path: Path) -> None:
    """Create .editorconfig, assert editorconfig_path is set."""
    (tmp_path / ".editorconfig").write_text("root = true\n[*]\nindent_style = space\n")
    analyzer = ConventionsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.editorconfig_path == ".editorconfig"


def test_detects_kebab_case_file_naming(tmp_path: Path) -> None:
    """Create src/ with kebab-case files, assert file_naming_convention == 'kebab-case'."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "my-component.ts").write_text("export const x = 1;")
    (src / "my-utils.ts").write_text("export const y = 2;")
    (src / "data-service.ts").write_text("export const z = 3;")
    (src / "api-client.ts").write_text("export const w = 4;")
    analyzer = ConventionsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.file_naming_convention == "kebab-case"


def test_empty_repo(tmp_path: Path) -> None:
    """Empty repo, assert linter is None."""
    analyzer = ConventionsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.linter is None
    assert result.formatter is None


def test_anti_pattern_no_linter(tmp_path: Path) -> None:
    """No linter config, should trigger anti-pattern."""
    analyzer = ConventionsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("no linter" in ap.lower() for ap in result.anti_patterns)


def test_anti_pattern_no_formatter(tmp_path: Path) -> None:
    """No formatter config, should trigger anti-pattern."""
    analyzer = ConventionsAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("no formatter" in ap.lower() for ap in result.anti_patterns)
