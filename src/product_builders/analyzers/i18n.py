"""i18n/l10n Analyzer — Dimension 6 (HIGH IMPACT).

Detects internationalization framework, translation file format,
directories, locales, and string externalization patterns.
"""

from __future__ import annotations

from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, I18nResult

_I18N_LIBS: dict[str, str] = {
    "i18next": "i18next",
    "react-i18next": "i18next",
    "next-i18next": "i18next",
    "vue-i18n": "vue-i18n",
    "@nuxtjs/i18n": "vue-i18n",
    "react-intl": "react-intl",
    "@formatjs/intl": "formatjs",
    "angular-i18n": "angular-i18n",
    "@angular/localize": "angular-localize",
    "next-intl": "next-intl",
    "gettext": "gettext",
    "django.utils.translation": "django-i18n",
    "babel": "babel",
    "fluent": "fluent",
    "svelte-i18n": "svelte-i18n",
    "typesafe-i18n": "typesafe-i18n",
    "@lingui/react": "lingui",
    "@lingui/core": "lingui",
    "@inlang/paraglide-js": "paraglide",
    "rosetta": "rosetta",
    "@messageformat/core": "icu-messageformat",
}


class I18nAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "i18n/l10n Analyzer"

    @property
    def dimension(self) -> str:
        return "i18n"

    def analyze(self, repo_path: Path, *, index=None) -> I18nResult:
        framework = self._detect_framework(repo_path)
        file_format, directories = self._detect_translation_files(repo_path)
        default_locale, locales = self._detect_locales(repo_path, directories)
        pattern = self._detect_externalization_pattern(repo_path)

        return I18nResult(
            status=AnalysisStatus.SUCCESS,
            i18n_framework=framework,
            translation_file_format=file_format,
            translation_directories=directories,
            default_locale=default_locale,
            supported_locales=locales,
            string_externalization_pattern=pattern,
        )

    def _detect_framework(self, repo_path: Path) -> str | None:
        pkg = self.read_json(repo_path / "package.json")
        if pkg:
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            for lib, name in _I18N_LIBS.items():
                if lib in deps:
                    return name
        req = repo_path / "requirements.txt"
        if req.exists():
            content = self.read_file(req)
            if content:
                lower = content.lower()
                if "django" in lower:
                    for line in content.splitlines():
                        if "django" in line.lower() and not line.strip().startswith("#"):
                            locale_dir = repo_path / "locale"
                            if locale_dir.is_dir():
                                return "django-i18n"
                if "flask-babel" in lower:
                    return "flask-babel"
                if "babel" in lower:
                    return "babel"
        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists():
            content = self.read_file(pyproject)
            if content and "babel" in content:
                return "babel"
        return None

    def _detect_translation_files(self, repo_path: Path) -> tuple[str | None, list[str]]:
        dirs: list[str] = []
        file_format: str | None = None

        candidates = [
            "locales", "locale", "i18n", "translations",
            "src/locales", "src/i18n", "src/translations",
            "public/locales", "assets/locales", "resources/lang",
        ]
        for d in candidates:
            if (repo_path / d).is_dir():
                dirs.append(d)

        if dirs:
            scan_dir = repo_path / dirs[0]
            json_files = list(scan_dir.rglob("*.json"))
            yaml_files = list(scan_dir.rglob("*.yaml")) + list(scan_dir.rglob("*.yml"))
            po_files = list(scan_dir.rglob("*.po"))
            xliff_files = list(scan_dir.rglob("*.xliff")) + list(scan_dir.rglob("*.xlf"))

            if json_files:
                file_format = "json"
            elif yaml_files:
                file_format = "yaml"
            elif po_files:
                file_format = "po"
            elif xliff_files:
                file_format = "xliff"

        return file_format, dirs

    def _detect_locales(self, repo_path: Path, translation_dirs: list[str]) -> tuple[str | None, list[str]]:
        locales: list[str] = []
        default: str | None = None

        for d in translation_dirs:
            full = repo_path / d
            if not full.is_dir():
                continue
            for child in sorted(full.iterdir()):
                if child.is_dir():
                    name = child.name
                    if len(name) in (2, 5) and name.replace("-", "").replace("_", "").isalpha():
                        locales.append(name)
                elif child.is_file() and child.suffix in (".json", ".yaml", ".yml"):
                    stem = child.stem
                    if len(stem) in (2, 5) and stem.replace("-", "").replace("_", "").isalpha():
                        locales.append(stem)

        for candidate in ("en", "en-US", "en_US"):
            if candidate in locales:
                default = candidate
                break
        if not default and locales:
            default = locales[0]

        return default, sorted(set(locales))

    def _detect_externalization_pattern(self, repo_path: Path) -> str | None:
        pkg = self.read_json(repo_path / "package.json")
        if pkg:
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "react-i18next" in deps or "i18next" in deps:
                return "t('key')"
            if "react-intl" in deps:
                return "intl.formatMessage({ id: 'key' })"
            if "vue-i18n" in deps:
                return "$t('key')"
            if "next-intl" in deps:
                return "t('key')"
        return None


register(I18nAnalyzer())
