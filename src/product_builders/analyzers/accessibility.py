"""Accessibility Analyzer — Dimension 16 (MEDIUM IMPACT).

Detects WCAG compliance level, a11y testing tools, ARIA usage,
semantic HTML patterns, keyboard navigation, and color contrast config.
"""

from __future__ import annotations

from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer, SKIP_DIRS
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AccessibilityResult, AnalysisStatus

_A11Y_TOOLS: dict[str, str] = {
    "axe-core": "axe-core",
    "@axe-core/react": "axe-core",
    "jest-axe": "jest-axe",
    "react-axe": "react-axe",
    "pa11y": "pa11y",
    "lighthouse": "lighthouse",
    "@testing-library/jest-dom": "testing-library",
    "eslint-plugin-jsx-a11y": "eslint-plugin-jsx-a11y",
    "vue-axe": "vue-axe",
    "@axe-core/playwright": "axe-playwright",
    "cypress-axe": "cypress-axe",
    "@storybook/addon-a11y": "storybook-a11y",
    "vitest-axe": "vitest-axe",
    "eslint-plugin-vuejs-accessibility": "eslint-vuejs-a11y",
    "focus-trap-react": "focus-trap",
    "focus-trap": "focus-trap",
}


class AccessibilityAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Accessibility Analyzer"

    @property
    def dimension(self) -> str:
        return "accessibility"

    def analyze(self, repo_path: Path, *, index=None) -> AccessibilityResult:
        wcag = self._detect_wcag_level(repo_path)
        tools = self._detect_a11y_tools(repo_path)
        aria = self._detect_aria_usage(repo_path)
        semantic = self._detect_semantic_html(repo_path)
        keyboard = self._detect_keyboard_nav(repo_path)
        contrast = self._detect_color_contrast(repo_path)

        # C19: Form accessibility detection
        form_a11y: list[str] = []
        for f in self.find_files(repo_path, "src/**/*.tsx", "src/**/*.jsx", "**/*.html")[:20]:
            content = self.read_file(f)
            if not content:
                continue
            if 'htmlFor=' in content or ' for=' in content:
                if "label-association" not in form_a11y:
                    form_a11y.append("label-association")
            if 'aria-required' in content:
                if "aria-required" not in form_a11y:
                    form_a11y.append("aria-required")
            if 'aria-invalid' in content:
                if "aria-invalid" not in form_a11y:
                    form_a11y.append("aria-invalid")
            if '<fieldset' in content:
                if "fieldset-legend" not in form_a11y:
                    form_a11y.append("fieldset-legend")

        # C20: Focus management detection
        focus_patterns: list[str] = []
        dep_names = self._collect_dep_names(repo_path)
        if "focus-trap-react" in dep_names or "focus-trap" in dep_names:
            focus_patterns.append("focus-trap")

        for f in self.find_files(repo_path, "src/**/*.tsx", "src/**/*.jsx", "**/*.html")[:15]:
            content = self.read_file(f)
            if not content:
                continue
            if "skip" in content.lower() and ("main" in content.lower() or "content" in content.lower()) and ("href" in content or "id=" in content):
                if "skip-link" not in focus_patterns:
                    focus_patterns.append("skip-link")
            if "focus-visible" in content or ":focus-visible" in content:
                if "focus-visible" not in focus_patterns:
                    focus_patterns.append("focus-visible")

        return AccessibilityResult(
            status=AnalysisStatus.SUCCESS,
            wcag_level=wcag,
            a11y_testing_tools=tools,
            aria_usage_detected=aria,
            semantic_html_score=semantic,
            keyboard_navigation=keyboard,
            color_contrast_config=contrast,
            form_accessibility=form_a11y,
            focus_management_patterns=focus_patterns,
        )

    def _detect_wcag_level(self, repo_path: Path) -> str | None:
        for config_name in ("axe.config.js", "axe.config.json", ".pa11yci", "pa11y.json"):
            path = repo_path / config_name
            if path.exists():
                content = self.read_file(path)
                if content:
                    if "AAA" in content:
                        return "AAA"
                    if "AA" in content:
                        return "AA"
                    return "A"
        return None

    def _detect_a11y_tools(self, repo_path: Path) -> list[str]:
        tools: list[str] = []
        pkg = self.read_json(repo_path / "package.json")
        if pkg:
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            for lib, name in _A11Y_TOOLS.items():
                if lib in deps and name not in tools:
                    tools.append(name)
        return tools

    def _detect_aria_usage(self, repo_path: Path) -> bool:
        src = repo_path / "src"
        scan = src if src.is_dir() else repo_path
        count = 0
        for ext in ("*.tsx", "*.jsx", "*.vue", "*.html"):
            for f in scan.rglob(ext):
                if count >= 30:
                    break
                if any(s in f.parts for s in SKIP_DIRS):
                    continue
                content = self.read_file(f)
                if content and ("aria-" in content or "role=" in content):
                    return True
                count += 1
        return False

    def _detect_semantic_html(self, repo_path: Path) -> str | None:
        src = repo_path / "src"
        scan = src if src.is_dir() else repo_path
        semantic_tags = ("<nav", "<main", "<article", "<section", "<header", "<footer", "<aside")
        semantic_count = 0
        div_count = 0
        files_checked = 0
        for ext in ("*.tsx", "*.jsx", "*.vue", "*.html"):
            if files_checked >= 30:
                break
            for f in scan.rglob(ext):
                if files_checked >= 30:
                    break
                if any(s in f.parts for s in SKIP_DIRS):
                    continue
                content = self.read_file(f)
                if not content:
                    continue
                files_checked += 1
                for tag in semantic_tags:
                    semantic_count += content.count(tag)
                div_count += content.count("<div")

        if files_checked == 0:
            return None
        total = semantic_count + div_count
        if total == 0:
            return None
        ratio = semantic_count / total
        if ratio > 0.3:
            return "high"
        if ratio > 0.1:
            return "medium"
        return "low"

    def _detect_keyboard_nav(self, repo_path: Path) -> bool:
        src = repo_path / "src"
        scan = src if src.is_dir() else repo_path
        count = 0
        for ext in ("*.tsx", "*.jsx", "*.vue"):
            for f in scan.rglob(ext):
                if count >= 20:
                    break
                if any(s in f.parts for s in SKIP_DIRS):
                    continue
                content = self.read_file(f)
                if content and ("onKeyDown" in content or "onKeyPress" in content or "tabIndex" in content or "tabindex" in content):
                    return True
                count += 1
        return False

    def _detect_color_contrast(self, repo_path: Path) -> str | None:
        pkg = self.read_json(repo_path / "package.json")
        if pkg:
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "eslint-plugin-jsx-a11y" in deps:
                return "eslint-plugin-jsx-a11y (includes contrast checks)"
        return None


register(AccessibilityAnalyzer())
