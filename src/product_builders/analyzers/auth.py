"""Authentication & Authorization Analyzer — Dimension 3 (CRITICAL).

Detects auth strategy (JWT, session, OAuth, etc.), auth middleware,
permission models, protected route patterns, and auth-related directories.
CRITICAL because incorrect auth patterns can create security breaches.
"""

from __future__ import annotations

import re
from pathlib import Path

from product_builders.analyzers.base import SKIP_DIRS, BaseAnalyzer
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, AuthResult

AUTH_STRATEGY_INDICATORS: dict[str, list[str]] = {
    "jwt": [
        "jsonwebtoken", "jose", "jwt", "PyJWT", "pyjwt",
        "jwt-decode", "@nestjs/jwt", "flask-jwt-extended",
        "djangorestframework-simplejwt", "System.IdentityModel.Tokens.Jwt",
    ],
    "session": [
        "express-session", "cookie-session", "flask-session",
        "django.contrib.sessions",
    ],
    "oauth": [
        "passport", "passport-oauth2", "passport-google-oauth20",
        "oauthlib", "django-oauth-toolkit", "authlib",
        "next-auth", "@auth/core", "lucia", "lucia-auth",
    ],
    "saml": ["passport-saml", "saml2-js", "python3-saml", "django-saml2-auth"],
    "basic": ["passport-http", "express-basic-auth"],
    "api_key": ["passport-headerapikey"],
    "firebase": ["firebase-admin", "@firebase/auth"],
    "auth0": ["@auth0/nextjs-auth0", "auth0", "auth0-python"],
    "cognito": ["amazon-cognito-identity-js", "boto3"],
    "clerk": ["@clerk/nextjs", "@clerk/clerk-sdk-node"],
    "supabase": ["@supabase/auth-helpers-nextjs", "@supabase/supabase-js"],
}

PERMISSION_MODEL_INDICATORS: dict[str, list[str]] = {
    "rbac": ["role", "roles", "hasRole", "isAdmin", "ROLE_", "RolesGuard", "role_required"],
    "abac": ["policy", "policies", "can", "ability", "casl", "@casl/ability"],
    "acl": ["acl", "access-control", "permission", "permissions"],
}

AUTH_DIRECTORY_PATTERNS = [
    "src/auth", "src/authentication", "auth", "authentication",
    "src/middleware/auth", "app/auth", "lib/auth",
    "src/guards", "app/guards",
    "src/policies", "app/policies",
]

AUTH_FILE_PATTERNS = [
    "**/auth*.py", "**/auth*.ts", "**/auth*.js", "**/auth*.java", "**/auth*.cs",
    "**/middleware/auth*", "**/guards/*Guard*", "**/guards/*guard*",
    "**/*passport*", "**/*strategy*",
]


class AuthAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Auth Patterns Analyzer"

    @property
    def dimension(self) -> str:
        return "auth"

    def analyze(self, repo_path: Path) -> AuthResult:
        dep_names = self._collect_dep_names(repo_path)
        strategy = self._detect_strategy(dep_names)
        middleware = self._detect_middleware(repo_path, dep_names)
        permission_model = self._detect_permission_model(repo_path, dep_names)
        protected_patterns = self._detect_protected_routes(repo_path)
        auth_dirs = self._detect_auth_directories(repo_path)

        return AuthResult(
            status=AnalysisStatus.SUCCESS,
            auth_strategy=strategy,
            auth_middleware=middleware,
            permission_model=permission_model,
            protected_route_patterns=protected_patterns,
            auth_directories=auth_dirs,
        )

    def _collect_dep_names(self, repo_path: Path) -> set[str]:
        deps: set[str] = set()
        pkg_json = repo_path / "package.json"
        if pkg_json.exists():
            data = self.read_json(pkg_json)
            if data:
                for section in ["dependencies", "devDependencies"]:
                    deps.update(data.get(section, {}).keys())

        for req_file in self.find_files(repo_path, "requirements*.txt"):
            content = self.read_file(req_file)
            if content:
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith(("#", "-")):
                        name = re.split(r"[><=!~\[]", line)[0].strip()
                        if name:
                            deps.add(name)

        return deps

    def _detect_strategy(self, dep_names: set[str]) -> str | None:
        for strategy, indicators in AUTH_STRATEGY_INDICATORS.items():
            if any(ind in dep_names for ind in indicators):
                return strategy
        return None

    def _detect_middleware(self, repo_path: Path, dep_names: set[str]) -> list[str]:
        middleware: list[str] = []

        if "passport" in dep_names:
            middleware.append("passport")
            # Detect passport strategies
            for dep in dep_names:
                if dep.startswith("passport-") and dep != "passport":
                    middleware.append(dep)

        known_middleware = {
            "express-jwt": "express-jwt",
            "koa-jwt": "koa-jwt",
            "@nestjs/passport": "nestjs-passport",
            "helmet": "helmet",
            "cors": "cors",
            "csurf": "csurf",
            "django.contrib.auth": "django-auth",
            "flask-login": "flask-login",
        }
        for dep, name in known_middleware.items():
            if dep in dep_names:
                middleware.append(name)

        # Scan for auth middleware files
        for pattern in ["**/middleware/auth*", "**/middleware/*auth*"]:
            for f in self.find_files(repo_path, pattern):
                if not any(skip in f.parts for skip in SKIP_DIRS):
                    middleware.append(str(f.relative_to(repo_path)))
                    break

        return middleware

    def _detect_permission_model(self, repo_path: Path, dep_names: set[str]) -> str | None:
        # Check dependencies first
        if "@casl/ability" in dep_names or "casl" in dep_names:
            return "abac"

        # Scan source files for patterns
        src_dir = repo_path / "src"
        scan_dir = src_dir if src_dir.is_dir() else repo_path
        count = 0

        for path in scan_dir.rglob("*"):
            if count >= 30:
                break
            if not path.is_file() or any(s in path.parts for s in SKIP_DIRS):
                continue
            if path.suffix not in (".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".cs", ".rb"):
                continue

            content = self.read_file(path)
            if not content:
                continue
            count += 1

            for model, indicators in PERMISSION_MODEL_INDICATORS.items():
                for ind in indicators:
                    if ind in content:
                        return model

        return None

    def _detect_protected_routes(self, repo_path: Path) -> list[str]:
        patterns: list[str] = []

        # Look for common guard/decorator patterns
        src_dir = repo_path / "src"
        scan_dir = src_dir if src_dir.is_dir() else repo_path
        count = 0

        for path in scan_dir.rglob("*"):
            if count >= 20:
                break
            if not path.is_file() or any(s in path.parts for s in SKIP_DIRS):
                continue
            if path.suffix not in (".ts", ".tsx", ".js", ".jsx", ".py", ".java"):
                continue

            content = self.read_file(path)
            if not content:
                continue
            count += 1

            guard_patterns = [
                r"@UseGuards\((\w+)\)",
                r"@login_required",
                r"@permission_required",
                r"@requires_auth",
                r"isAuthenticated",
                r"ensureAuthenticated",
                r"protect\(",
                r"requireAuth",
                r"withAuth",
            ]
            for pat in guard_patterns:
                matches = re.findall(pat, content)
                if matches:
                    for m in matches:
                        p = m if isinstance(m, str) and m else pat.strip("\\()")
                        if p not in patterns:
                            patterns.append(p)

        return patterns[:10]

    def _detect_auth_directories(self, repo_path: Path) -> list[str]:
        dirs: list[str] = []
        for d in AUTH_DIRECTORY_PATTERNS:
            if (repo_path / d).is_dir():
                dirs.append(d)
        return dirs


register(AuthAnalyzer())
