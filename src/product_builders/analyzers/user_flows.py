"""User Flows Analyzer.

Detects route structure, navigation patterns, auth-protected routes,
error/404 pages, and page directories.
"""

from __future__ import annotations

from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer, SKIP_DIRS
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, UserFlowsResult


class UserFlowsAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "User Flows Analyzer"

    @property
    def dimension(self) -> str:
        return "user_flows"

    def analyze(self, repo_path: Path, *, index=None) -> UserFlowsResult:
        page_dirs = self._detect_page_dirs(repo_path)
        route_files, route_count = self._detect_routes(repo_path, page_dirs)
        nav_type = self._detect_navigation_type(repo_path)
        auth_protected = self._detect_auth_routes(repo_path)
        has_404 = self._detect_404(repo_path, page_dirs)
        has_error = self._detect_error_page(repo_path, page_dirs)

        # C14: Detect dynamic route parameters
        dynamic_routes: list[str] = []
        dynamic_patterns = ["[", "]", "$"]  # [id], [...slug], $param
        for page_dir in page_dirs:
            dir_path = repo_path / page_dir
            if dir_path.is_dir():
                for f in dir_path.rglob("*"):
                    if f.is_file() and any(p in f.name for p in dynamic_patterns):
                        rel = str(f.relative_to(repo_path))
                        dynamic_routes.append(rel)

        # C14: Detect lazy routes
        lazy_routes = False
        for route_file in route_files[:20]:
            content = self.read_file(repo_path / route_file)
            if content and ("React.lazy" in content or "dynamic(" in content or "lazy(" in content):
                lazy_routes = True
                break

        return UserFlowsResult(
            status=AnalysisStatus.SUCCESS,
            route_count=route_count,
            route_files=route_files,
            navigation_type=nav_type,
            auth_protected_routes=auth_protected,
            has_404_page=has_404,
            has_error_page=has_error,
            page_directories=page_dirs,
            dynamic_routes=dynamic_routes,
            lazy_routes=lazy_routes,
        )

    def _detect_page_dirs(self, repo_path: Path) -> list[str]:
        candidates = [
            "src/pages", "pages", "src/views", "views",
            "src/app", "app", "src/screens", "screens",
            "src/routes", "routes",
        ]
        return [d for d in candidates if (repo_path / d).is_dir()]

    def _detect_routes(self, repo_path: Path, page_dirs: list[str]) -> tuple[list[str], int]:
        route_files: list[str] = []

        for page_dir in page_dirs:
            full = repo_path / page_dir
            for f in full.rglob("*"):
                if not f.is_file():
                    continue
                if any(s in f.parts for s in SKIP_DIRS):
                    continue
                if f.suffix in (".tsx", ".jsx", ".vue", ".svelte", ".ts", ".js", ".py"):
                    try:
                        rel = str(f.relative_to(repo_path))
                    except ValueError:
                        rel = str(f)
                    route_files.append(rel)

        if not route_files:
            src = repo_path / "src"
            scan = src if src.is_dir() else repo_path
            for f in scan.rglob("*"):
                if not f.is_file():
                    continue
                if any(s in f.parts for s in SKIP_DIRS):
                    continue
                name_lower = f.stem.lower()
                if "route" in name_lower or "router" in name_lower:
                    if f.suffix in (".tsx", ".jsx", ".ts", ".js"):
                        try:
                            rel = str(f.relative_to(repo_path))
                        except ValueError:
                            rel = str(f)
                        route_files.append(rel)

        total = len(route_files)
        return route_files[:30], total

    def _detect_navigation_type(self, repo_path: Path) -> str | None:
        pkg = self.read_json(repo_path / "package.json")
        if pkg:
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "next" in deps:
                if (repo_path / "src" / "app").is_dir() or (repo_path / "app").is_dir():
                    return "next-app-router"
                return "next-pages-router"
            if "react-router-dom" in deps or "react-router" in deps:
                return "react-router"
            if "vue-router" in deps:
                return "vue-router"
            if "@angular/router" in deps:
                return "angular-router"
            if "wouter" in deps:
                return "wouter"

        if (repo_path / "src" / "pages").is_dir() or (repo_path / "pages").is_dir():
            return "file-based"
        return None

    def _detect_auth_routes(self, repo_path: Path) -> bool:
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
                if any(pattern in content for pattern in [
                    "ProtectedRoute", "PrivateRoute", "AuthRoute",
                    "requireAuth", "isAuthenticated", "withAuth",
                    "authGuard", "canActivate", "middleware",
                ]):
                    return True
        return False

    def _detect_404(self, repo_path: Path, page_dirs: list[str]) -> bool:
        for page_dir in page_dirs:
            full = repo_path / page_dir
            for f in full.rglob("*"):
                if not f.is_file():
                    continue
                name = f.stem.lower()
                if "404" in name or "not-found" in name or "notfound" in name or "not_found" in name:
                    return True
        return False

    def _detect_error_page(self, repo_path: Path, page_dirs: list[str]) -> bool:
        for page_dir in page_dirs:
            full = repo_path / page_dir
            for f in full.rglob("*"):
                if not f.is_file():
                    continue
                name = f.stem.lower()
                if name in ("error", "_error", "500", "error-page"):
                    return True
        return False


register(UserFlowsAnalyzer())
