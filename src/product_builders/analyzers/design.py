"""Design/UI Analyzer — Dimension 15 (MEDIUM IMPACT).

Detects CSS methodology, component library, design tokens,
responsive strategy, theme provider, and shared design system usage.
"""

from __future__ import annotations

from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer, SKIP_DIRS
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, DesignUIResult

_COMPONENT_LIBS: dict[str, str] = {
    "@mui/material": "material-ui",
    "@material-ui/core": "material-ui",
    "antd": "ant-design",
    "@ant-design/icons": "ant-design",
    "@chakra-ui/react": "chakra-ui",
    "@mantine/core": "mantine",
    "primereact": "PrimeReact",
    "primevue": "primevue",
    "@radix-ui/react-dialog": "radix-ui",
    "@headlessui/react": "headless-ui",
    "vuetify": "vuetify",
    "quasar": "quasar",
    "bootstrap": "bootstrap",
    "react-bootstrap": "react-bootstrap",
    "@cegid/cds-react": "cds",
    "shadcn": "shadcn",
    "@shadcn/ui": "shadcn",
    "@base-ui/react": "base-ui",
    "@nextui-org/react": "nextui",
    "@park-ui/react": "park-ui",
    "daisyui": "daisyui",
    "@ark-ui/react": "Ark UI",
    "@ark-ui/vue": "Ark UI",
    "@ark-ui/solid": "Ark UI",
    "react-aria": "React Aria",
    "react-aria-components": "React Aria",
    "flowbite": "Flowbite",
    "flowbite-react": "Flowbite",
    "@heroui/react": "HeroUI",
    "@skeletonlabs/skeleton": "Skeleton",
    "element-plus": "Element Plus",
    "naive-ui": "Naive UI",
    "@angular/material": "Angular Material",
    "primeng": "PrimeNG",
}

_CSS_METHODOLOGIES: dict[str, str] = {
    "tailwindcss": "tailwind",
    "tailwind.config.js": "tailwind",
    "tailwind.config.ts": "tailwind",
    "styled-components": "css-in-js",
    "@emotion/react": "css-in-js",
    "@emotion/styled": "css-in-js",
    "sass": "scss",
    "node-sass": "scss",
    "less": "less",
    "@vanilla-extract/css": "vanilla-extract",
    "@pandacss/dev": "panda-css",
    "@stylexjs/stylex": "stylex",
    "unocss": "unocss",
    "@linaria/core": "linaria",
    "lightningcss": "lightningcss",
}


class DesignUIAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Design/UI Analyzer"

    @property
    def dimension(self) -> str:
        return "design_ui"

    def analyze(self, repo_path: Path, *, index=None) -> DesignUIResult:
        component_lib, component_version = self._detect_component_library(repo_path)
        css_method = self._detect_css_methodology(repo_path)
        tokens_format, tokens_path = self._detect_design_tokens(repo_path)
        responsive = self._detect_responsive(repo_path)
        theme = self._detect_theme_provider(repo_path)
        styling_dirs = self._detect_styling_dirs(repo_path)
        uses_shared_ds, ds_name = self._detect_shared_design_system(repo_path)

        if not css_method:
            src = repo_path / "src"
            scan = src if src.is_dir() else repo_path
            for pattern in ("*.module.css", "*.module.scss"):
                found = False
                for f in scan.rglob(pattern):
                    if any(s in f.parts for s in SKIP_DIRS):
                        continue
                    css_method = "css-modules"
                    found = True
                    break
                if found:
                    break

        # Collect deps once for C12/C13/C28 detections
        deps = self._collect_dep_names(repo_path)

        # C12: Icon library detection
        icon_libs = {
            "lucide-react": "lucide", "@lucide/react": "lucide",
            "@heroicons/react": "heroicons", "heroicons": "heroicons",
            "@phosphor-icons/react": "phosphor",
            "@tabler/icons-react": "tabler",
            "react-icons": "react-icons",
            "@iconify/react": "iconify",
            "@fortawesome/fontawesome-free": "fontawesome",
            "@mui/icons-material": "material-icons",
            "feather-icons": "feather",
        }
        icon_library = None
        for dep, name in icon_libs.items():
            if dep in deps:
                icon_library = name
                break

        # C13: Storybook / component documentation detection
        component_doc_tool = None
        if (repo_path / ".storybook").is_dir():
            component_doc_tool = "storybook"
        else:
            doc_deps = {"histoire": "histoire", "@ladle/react": "ladle"}
            for dep, name in doc_deps.items():
                if dep in deps:
                    component_doc_tool = name
                    break

        # C28: Font strategy detection
        font_strategy = None
        font_deps = {
            "@next/font": "next-font",
            "@fontsource/inter": "fontsource", "@fontsource/roboto": "fontsource",
        }
        for dep, name in font_deps.items():
            if dep in deps:
                font_strategy = name
                break
        if not font_strategy:
            for html_file in self.find_files(repo_path, "**/*.html", "src/**/index.html")[:5]:
                content = self.read_file(html_file)
                if content and "fonts.googleapis.com" in content:
                    font_strategy = "google-fonts-cdn"
                    break

        return DesignUIResult(
            status=AnalysisStatus.SUCCESS,
            css_methodology=css_method,
            component_library=component_lib,
            component_library_version=component_version,
            design_tokens_format=tokens_format,
            design_tokens_path=tokens_path,
            responsive_strategy=responsive,
            theme_provider=theme,
            styling_directories=styling_dirs,
            uses_shared_design_system=uses_shared_ds,
            shared_design_system_name=ds_name,
            icon_library=icon_library,
            component_doc_tool=component_doc_tool,
            font_strategy=font_strategy,
        )

    def _detect_component_library(self, repo_path: Path) -> tuple[str | None, str | None]:
        pkg = self.read_json(repo_path / "package.json")
        if not pkg:
            return None, None
        all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        for lib, name in _COMPONENT_LIBS.items():
            if lib in all_deps:
                return name, all_deps.get(lib)
        return None, None

    def _detect_css_methodology(self, repo_path: Path) -> str | None:
        for filename in ("tailwind.config.js", "tailwind.config.ts", "tailwind.config.cjs", "tailwind.config.mjs"):
            if (repo_path / filename).exists():
                return "tailwind"
        pkg = self.read_json(repo_path / "package.json")
        if pkg:
            all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            for lib, method in _CSS_METHODOLOGIES.items():
                if lib in all_deps:
                    return method
        return None

    def _detect_design_tokens(self, repo_path: Path) -> tuple[str | None, str | None]:
        candidates = [
            ("tokens.json", "json"), ("design-tokens.json", "json"),
            ("tokens.yaml", "yaml"), ("design-tokens.yaml", "yaml"),
            ("tokens.scss", "scss"), ("_tokens.scss", "scss"),
            ("tokens.css", "css-custom-properties"),
        ]
        for filename, fmt in candidates:
            for root in self._design_token_search_roots(repo_path):
                if not root.is_dir():
                    continue
                for f in root.rglob(filename):
                    if any(s in f.parts for s in SKIP_DIRS):
                        continue
                    try:
                        return fmt, str(f.relative_to(repo_path))
                    except ValueError:
                        return fmt, str(f)
        return None, None

    def _design_token_search_roots(self, repo_path: Path) -> list[Path]:
        """Prefer app source trees; avoid whole-repo rglob into vendor dirs."""
        roots: list[Path] = []
        for name in ("src", "app", "libs", "design", "packages"):
            p = repo_path / name
            if p.is_dir():
                roots.append(p)
        pkgs = repo_path / "packages"
        if pkgs.is_dir():
            for sub in pkgs.iterdir():
                if sub.is_dir():
                    roots.append(sub)
        if not roots:
            roots.append(repo_path)
        return roots

    def _detect_responsive(self, repo_path: Path) -> str | None:
        pkg = self.read_json(repo_path / "package.json")
        if pkg:
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "tailwindcss" in deps:
                return "tailwind-responsive"
            if "@mui/material" in deps or "@material-ui/core" in deps:
                return "material-breakpoints"
        return None

    def _detect_theme_provider(self, repo_path: Path) -> str | None:
        pkg = self.read_json(repo_path / "package.json")
        if pkg:
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "styled-components" in deps:
                return "styled-components ThemeProvider"
            if "@emotion/react" in deps:
                return "emotion ThemeProvider"
            if "@mui/material" in deps:
                return "MUI ThemeProvider"
        return None

    def _detect_styling_dirs(self, repo_path: Path) -> list[str]:
        candidates = ["src/styles", "src/css", "styles", "css", "src/assets/styles", "src/theme"]
        return [d for d in candidates if (repo_path / d).is_dir()]

    def _detect_shared_design_system(self, repo_path: Path) -> tuple[bool, str | None]:
        pkg = self.read_json(repo_path / "package.json")
        if not pkg:
            return False, None
        all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        if "@cegid/cds-react" in all_deps:
            return True, "CDS (Cegid Design System)"
        return False, None


register(DesignUIAnalyzer())
