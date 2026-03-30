from __future__ import annotations

"""Tests for i18n/l10n analyzer."""
import json
from pathlib import Path

from product_builders.analyzers.i18n import I18nAnalyzer


def test_detects_i18next_framework(tmp_path: Path) -> None:
    """package.json with i18next dependency should detect i18next framework."""
    pkg = {"dependencies": {"i18next": "^23.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = I18nAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.i18n_framework == "i18next"


def test_detects_react_intl_framework(tmp_path: Path) -> None:
    """package.json with react-intl should detect react-intl framework."""
    pkg = {"dependencies": {"react-intl": "^6.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = I18nAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.i18n_framework == "react-intl"


def test_detects_translation_files_json(tmp_path: Path) -> None:
    """JSON files in locales/ should be detected as translation files."""
    locales = tmp_path / "locales"
    locales.mkdir()
    (locales / "en.json").write_text('{"hello": "Hello"}')
    (locales / "fr.json").write_text('{"hello": "Bonjour"}')
    analyzer = I18nAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert "locales" in result.translation_directories
    assert result.translation_file_format == "json"


def test_detects_supported_locales(tmp_path: Path) -> None:
    """Subdirectories in locales/ named with locale codes should be detected."""
    locales = tmp_path / "locales"
    locales.mkdir()
    (locales / "en").mkdir()
    (locales / "fr").mkdir()
    analyzer = I18nAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert "en" in result.supported_locales
    assert "fr" in result.supported_locales


def test_detects_default_locale(tmp_path: Path) -> None:
    """When en, fr, de locales exist, default_locale should be en."""
    locales = tmp_path / "locales"
    locales.mkdir()
    (locales / "en").mkdir()
    (locales / "fr").mkdir()
    (locales / "de").mkdir()
    analyzer = I18nAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.default_locale == "en"


def test_detects_rtl_languages(tmp_path: Path) -> None:
    """Arabic locale directory should be detected as RTL language."""
    locales = tmp_path / "locales"
    locales.mkdir()
    (locales / "ar").mkdir()
    (locales / "en").mkdir()
    analyzer = I18nAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert "ar" in result.rtl_languages


def test_detects_translation_management(tmp_path: Path) -> None:
    """Crowdin config file should detect crowdin as translation management."""
    pkg = {"dependencies": {"i18next": "^23.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    (tmp_path / ".crowdin.yml").write_text("project_id: 12345")
    analyzer = I18nAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.translation_management == "crowdin"


def test_empty_repo_no_i18n(tmp_path: Path) -> None:
    """Empty repo should have no i18n framework detected."""
    analyzer = I18nAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.i18n_framework is None


def test_anti_pattern_no_translation_management(tmp_path: Path) -> None:
    """i18next dep but no translation management should trigger anti-pattern."""
    pkg = {"dependencies": {"i18next": "^23.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    analyzer = I18nAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert any("translation management" in ap.lower() for ap in result.anti_patterns)
