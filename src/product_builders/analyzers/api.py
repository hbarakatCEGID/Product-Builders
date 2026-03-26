"""API Analyzer — Dimension 17 (MEDIUM IMPACT).

Detects API style (REST, GraphQL, gRPC), route structure,
OpenAPI specs, request validation, response format, pagination, and versioning.
"""

from __future__ import annotations

from pathlib import Path

from product_builders.analyzers.base import BaseAnalyzer, SKIP_DIRS
from product_builders.analyzers.deps import API_PYPROJECT_HINTS, VALIDATION_PACKAGE_TO_NAME
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, APIResult

_GRAPHQL_INDICATORS: list[str] = [
    "graphql", "@apollo/server", "apollo-server", "type-graphql",
    "ariadne", "strawberry-graphql", "graphene", "graphene-django",
    "@nestjs/graphql", "mercurius",
]

_GRPC_INDICATORS: list[str] = [
    "grpc", "@grpc/grpc-js", "grpcio", "protobuf",
]

_TRPC_INDICATORS: list[str] = [
    "@trpc/server", "@trpc/client",
]


class APIAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "API Analyzer"

    @property
    def dimension(self) -> str:
        return "api"

    def analyze(self, repo_path: Path, *, index=None) -> APIResult:
        api_style = self._detect_api_style(repo_path)
        route_structure = self._detect_route_structure(repo_path)
        api_dirs = self._detect_api_dirs(repo_path)
        openapi = self._detect_openapi(repo_path)
        validation = self._detect_validation(repo_path)
        response_format = self._detect_response_format(repo_path)
        pagination = self._detect_pagination(repo_path)
        versioning = self._detect_versioning(repo_path)

        # AST-enriched path: detect API style from route decorators and imports
        if index is not None and api_style is None:
            # Detect REST from route decorators
            rest_decorators = [
                "app.get", "app.post", "app.put", "app.delete", "app.patch",
                "router.get", "router.post", "router.put", "router.delete",
                "Get", "Post", "Put", "Delete",
            ]
            for dec in rest_decorators:
                if index.get_decorator_usage(dec):
                    api_style = "rest"
                    break

            # Detect GraphQL from imports
            if api_style is None:
                graphql_modules = [
                    "graphql", "@apollo", "type-graphql", "nexus",
                    "graphene", "strawberry",
                ]
                for mod in graphql_modules:
                    if index.who_imports(mod):
                        api_style = "graphql"
                        break

        result = APIResult(
            status=AnalysisStatus.SUCCESS,
            api_style=api_style,
            route_structure=route_structure,
            api_directories=api_dirs,
            openapi_spec_path=openapi,
            request_validation=validation,
            response_format=response_format,
            pagination_pattern=pagination,
            versioning_strategy=versioning,
        )

        anti_patterns = []
        if result.api_style == "rest" and not result.openapi_spec_path:
            anti_patterns.append("MEDIUM: REST API without OpenAPI spec — API documentation will be incomplete")
        if result.api_style and not result.request_validation:
            anti_patterns.append("HIGH: API detected but no request validation — will accept invalid input")
        result.anti_patterns = anti_patterns

        return result

    def _detect_api_style(self, repo_path: Path) -> str | None:
        deps = self.collect_dependency_names(
            repo_path, pyproject_substrings=API_PYPROJECT_HINTS
        )
        for indicator in _GRAPHQL_INDICATORS:
            if indicator in deps:
                return "graphql"
        for indicator in _GRPC_INDICATORS:
            if indicator in deps:
                return "grpc"
        for indicator in _TRPC_INDICATORS:
            if indicator in deps:
                return "trpc"
        if any(d in deps for d in ["express", "fastify", "koa", "hapi",
                                    "fastapi", "flask", "django", "djangorestframework",
                                    "@nestjs/core", "spring-boot-starter-web"]):
            return "rest"
        api_dir = repo_path / "src" / "api"
        routes_dir = repo_path / "src" / "routes"
        controllers_dir = repo_path / "src" / "controllers"
        if api_dir.is_dir() or routes_dir.is_dir() or controllers_dir.is_dir():
            return "rest"
        # Next.js App Router API routes (check known locations, avoid recursive glob)
        if "next" in deps:
            if (repo_path / "app" / "api").is_dir() or (repo_path / "src" / "app" / "api").is_dir():
                return "rest"
        return None

    def _detect_route_structure(self, repo_path: Path) -> str | None:
        if (repo_path / "src" / "pages").is_dir() or (repo_path / "pages").is_dir():
            return "file-based (Next.js/Nuxt)"
        if (repo_path / "src" / "app").is_dir():
            next_config = repo_path / "next.config.js"
            next_config_ts = repo_path / "next.config.ts"
            next_config_mjs = repo_path / "next.config.mjs"
            if next_config.exists() or next_config_ts.exists() or next_config_mjs.exists():
                return "app-router (Next.js)"
        if (repo_path / "src" / "routes").is_dir():
            return "directory-based (src/routes/)"
        if (repo_path / "src" / "controllers").is_dir():
            return "controller-based (src/controllers/)"
        return None

    def _detect_api_dirs(self, repo_path: Path) -> list[str]:
        candidates = [
            "src/api", "src/routes", "src/controllers", "api",
            "src/endpoints", "src/handlers", "app/api",
            "src/main/java", "src/routers",
        ]
        return [d for d in candidates if (repo_path / d).is_dir()]

    def _detect_openapi(self, repo_path: Path) -> str | None:
        candidates = [
            "openapi.yaml", "openapi.yml", "openapi.json",
            "swagger.yaml", "swagger.yml", "swagger.json",
            "docs/openapi.yaml", "docs/swagger.yaml",
            "api/openapi.yaml",
        ]
        for c in candidates:
            if (repo_path / c).exists():
                return c
        return None

    def _detect_validation(self, repo_path: Path) -> str | None:
        deps = self.collect_dependency_names(
            repo_path, pyproject_substrings=API_PYPROJECT_HINTS
        )
        for lib, name in VALIDATION_PACKAGE_TO_NAME.items():
            if lib in deps:
                return name
        return None

    def _detect_response_format(self, repo_path: Path) -> str | None:
        deps = self.collect_dependency_names(
            repo_path, pyproject_substrings=API_PYPROJECT_HINTS
        )
        if any(d in deps for d in _GRAPHQL_INDICATORS):
            return "json (GraphQL)"
        if any(d in deps for d in ["express", "fastify", "fastapi", "flask",
                                    "djangorestframework", "@nestjs/core"]):
            return "json"
        return None

    def _detect_pagination(self, repo_path: Path) -> str | None:
        src = repo_path / "src"
        scan = src if src.is_dir() else repo_path
        count = 0
        for ext in ("*.ts", "*.js", "*.py", "*.java"):
            for f in scan.rglob(ext):
                if count >= 50:
                    break
                if any(s in f.parts for s in SKIP_DIRS):
                    continue
                content = self.read_file(f)
                if not content:
                    continue
                count += 1
                if "cursor" in content.lower() and "pagination" in content.lower():
                    return "cursor-based"
                if "offset" in content.lower() and ("limit" in content.lower() or "page" in content.lower()):
                    return "offset-based"
        return None

    def _detect_versioning(self, repo_path: Path) -> str | None:
        api_dirs = self._detect_api_dirs(repo_path)
        for api_dir in api_dirs:
            full = repo_path / api_dir
            if full.is_dir():
                for child in full.iterdir():
                    if child.is_dir() and child.name in ("v1", "v2", "v3"):
                        return "url-path"
        return None


register(APIAnalyzer())
