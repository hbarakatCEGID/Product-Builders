"""Frontend Patterns Analyzer.

Detects layout patterns, form libraries, modal implementations,
list virtualization, error boundaries, loading patterns, routing,
and animation libraries.
"""

from __future__ import annotations

from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer, SKIP_DIRS
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, FrontendPatternsResult

_FORM_LIBS: dict[str, str] = {
    "react-hook-form": "react-hook-form",
    "formik": "formik",
    "final-form": "react-final-form",
    "react-final-form": "react-final-form",
    "@tanstack/react-form": "tanstack-form",
    "vee-validate": "vee-validate",
    "vuelidate": "vuelidate",
    "@angular/forms": "angular-forms",
    "sveltekit-superforms": "superforms",
}

_ROUTING_LIBS: dict[str, str] = {
    "react-router-dom": "react-router",
    "react-router": "react-router",
    "@tanstack/react-router": "tanstack-router",
    "vue-router": "vue-router",
    "@angular/router": "angular-router",
    "wouter": "wouter",
    "next": "next-router",
}

_ANIMATION_LIBS: dict[str, str] = {
    "framer-motion": "framer-motion",
    "motion": "framer-motion",
    "react-spring": "react-spring",
    "@react-spring/web": "react-spring",
    "gsap": "gsap",
    "animejs": "anime.js",
    "lottie-react": "lottie",
    "lottie-web": "lottie",
    "@formkit/auto-animate": "auto-animate",
    "react-transition-group": "react-transition-group",
    "@rive-app/react-canvas": "rive",
}

_VIRTUALIZATION_LIBS: dict[str, str] = {
    "react-window": "react-window",
    "react-virtualized": "react-virtualized",
    "@tanstack/react-virtual": "tanstack-virtual",
    "react-virtuoso": "react-virtuoso",
    "vue-virtual-scroller": "vue-virtual-scroller",
}


class FrontendPatternsAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Frontend Patterns Analyzer"

    @property
    def dimension(self) -> str:
        return "frontend_patterns"

    def analyze(self, repo_path: Path, *, index=None) -> FrontendPatternsResult:
        deps = self.collect_dependency_names(repo_path, include_requirements_txt=False)

        layout = self._detect_layout_patterns(repo_path, deps)
        forms = self._detect_form_libs(deps)
        modal = self._detect_modal_pattern(repo_path, deps)
        virtualization = self._detect_virtualization(deps)
        error_boundary = self._detect_error_boundary(repo_path)
        loading = self._detect_loading_patterns(repo_path)
        routing = self._detect_routing(deps)
        animation = self._detect_animation(deps)

        # AST-enriched path: detect patterns from actual component usage and imports
        if index is not None:
            # Detect error boundaries from AST
            if not error_boundary:
                components = index.get_components()
                component_names = {c.name for c in components}
                if "ErrorBoundary" in component_names:
                    error_boundary = True

            # Detect form libraries from actual imports
            form_libs = {
                "react-hook-form": "react-hook-form",
                "formik": "formik",
                "@mantine/form": "mantine-form",
                "react-final-form": "react-final-form",
            }
            for mod, lib_name in form_libs.items():
                if index.who_imports(mod):
                    if lib_name not in forms:
                        forms.append(lib_name)

        return FrontendPatternsResult(
            status=AnalysisStatus.SUCCESS,
            layout_patterns=layout,
            form_libraries=forms,
            modal_pattern=modal,
            list_virtualization=virtualization,
            error_boundary=error_boundary,
            loading_patterns=loading,
            routing_library=routing,
            animation_library=animation,
        )

    def _detect_layout_patterns(self, repo_path: Path, deps: set[str]) -> list[str]:
        patterns: list[str] = []
        if "tailwindcss" in deps:
            patterns.append("tailwind-flex/grid")
        if "@mui/material" in deps or "@material-ui/core" in deps:
            patterns.append("material-grid")
        if "@chakra-ui/react" in deps:
            patterns.append("chakra-layout")

        src = repo_path / "src"
        scan = src if src.is_dir() else repo_path
        layout_dirs = ["layouts", "layout", "src/layouts", "src/layout", "components/layouts"]
        for d in layout_dirs:
            if (repo_path / d).is_dir():
                patterns.append(f"layout-directory ({d})")
                break

        count = 0
        for ext in ("*.tsx", "*.jsx"):
            for f in scan.rglob(ext):
                if count >= 20:
                    break
                if any(s in f.parts for s in SKIP_DIRS):
                    continue
                content = self.read_file(f)
                if not content:
                    continue
                count += 1
                if "display: grid" in content or "display: 'grid'" in content:
                    if "css-grid" not in patterns:
                        patterns.append("css-grid")
                if "display: flex" in content or "display: 'flex'" in content:
                    if "flexbox" not in patterns:
                        patterns.append("flexbox")
        return patterns

    def _detect_form_libs(self, deps: set[str]) -> list[str]:
        found: list[str] = []
        for lib, name in _FORM_LIBS.items():
            if lib in deps and name not in found:
                found.append(name)
        return found

    def _detect_modal_pattern(self, repo_path: Path, deps: set[str]) -> str | None:
        if "@radix-ui/react-dialog" in deps:
            return "radix-dialog"
        if "@headlessui/react" in deps:
            return "headlessui-dialog"
        if "@mui/material" in deps:
            return "mui-dialog"
        if "react-modal" in deps:
            return "react-modal"

        src = repo_path / "src"
        scan = src if src.is_dir() else repo_path
        for ext in ("*.tsx", "*.jsx"):
            for f in scan.rglob(ext):
                if any(s in f.parts for s in SKIP_DIRS):
                    continue
                if "modal" in f.stem.lower() or "dialog" in f.stem.lower():
                    return "custom-modal"
        return None

    def _detect_virtualization(self, deps: set[str]) -> str | None:
        for lib, name in _VIRTUALIZATION_LIBS.items():
            if lib in deps:
                return name
        return None

    def _detect_error_boundary(self, repo_path: Path) -> bool:
        src = repo_path / "src"
        scan = src if src.is_dir() else repo_path
        count = 0
        for ext in ("*.tsx", "*.jsx", "*.ts", "*.js"):
            for f in scan.rglob(ext):
                if count >= 40:
                    break
                if any(s in f.parts for s in SKIP_DIRS):
                    continue
                content = self.read_file(f)
                if not content:
                    continue
                count += 1
                if "ErrorBoundary" in content or "componentDidCatch" in content:
                    return True
        return False

    def _detect_loading_patterns(self, repo_path: Path) -> list[str]:
        patterns: list[str] = []
        src = repo_path / "src"
        scan = src if src.is_dir() else repo_path
        count = 0
        for ext in ("*.tsx", "*.jsx"):
            for f in scan.rglob(ext):
                if count >= 30:
                    break
                if any(s in f.parts for s in SKIP_DIRS):
                    continue
                content = self.read_file(f)
                if not content:
                    continue
                count += 1
                if "Skeleton" in content and "skeleton" not in patterns:
                    patterns.append("skeleton")
                if "Spinner" in content or "spinner" in content.lower():
                    if "spinner" not in patterns:
                        patterns.append("spinner")
                if "Suspense" in content and "suspense" not in patterns:
                    patterns.append("suspense")
                if "isLoading" in content or "loading" in content:
                    if "loading-state" not in patterns:
                        patterns.append("loading-state")
        return patterns

    def _detect_routing(self, deps: set[str]) -> str | None:
        for lib, name in _ROUTING_LIBS.items():
            if lib in deps:
                return name
        return None

    def _detect_animation(self, deps: set[str]) -> str | None:
        for lib, name in _ANIMATION_LIBS.items():
            if lib in deps:
                return name
        return None


register(FrontendPatternsAnalyzer())
