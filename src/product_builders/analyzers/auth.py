"""Authentication & Authorization Analyzer — Dimension 3 (CRITICAL).

Detects auth strategy (JWT, session, OAuth, etc.), auth middleware,
permission models, protected route patterns, and auth-related directories.
CRITICAL because incorrect auth patterns can create security breaches.
"""

from __future__ import annotations

import re
from pathlib import Path

from product_builders.analyzers.base import (
    MAX_SOURCE_FILES_AUTH_PERMISSION,
    MAX_SOURCE_FILES_AUTH_PROTECTED,
    SKIP_DIRS,
    BaseAnalyzer,
)
from product_builders.analyzers.registry import register
from product_builders.models.analysis import AnalysisStatus, AuthResult

AUTH_STRATEGY_INDICATORS: dict[str, list[str]] = {
    "jwt": [
        "jsonwebtoken", "jose", "jwt", "PyJWT", "pyjwt",
        "jwt-decode", "@nestjs/jwt", "flask-jwt-extended",
        "djangorestframework-simplejwt", "System.IdentityModel.Tokens.Jwt",
        "golang-jwt/jwt", "jjwt", "io.jsonwebtoken",
    ],
    "session": [
        "express-session", "cookie-session", "flask-session",
        "django.contrib.sessions",
        "devise", "sorcery",
    ],
    "oauth": [
        "passport", "passport-oauth2", "passport-google-oauth20",
        "oauthlib", "django-oauth-toolkit", "authlib",
        "next-auth", "@auth/core", "lucia", "lucia-auth",
        "goth", "omniauth", "spring-boot-starter-oauth2-client",
    ],
    "webauthn": [
        "@simplewebauthn/server", "@simplewebauthn/browser",
        "py_webauthn", "go-webauthn", "webauthn4j",
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

    def analyze(self, repo_path: Path, *, index=None) -> AuthResult:
        dep_names = self._collect_dep_names(repo_path)
        strategy = self._detect_strategy(dep_names)
        middleware = self._detect_middleware(repo_path, dep_names)
        permission_model, protected_patterns = self._detect_permission_and_protected(
            repo_path, dep_names
        )
        auth_dirs = self._detect_auth_directories(repo_path)
        oauth_providers = self._detect_oauth_providers(repo_path)
        mfa_methods = self._detect_mfa_methods(dep_names)

        result = AuthResult(
            status=AnalysisStatus.SUCCESS,
            auth_strategy=strategy,
            auth_middleware=middleware,
            permission_model=permission_model,
            protected_route_patterns=protected_patterns,
            auth_directories=auth_dirs,
            oauth_providers=oauth_providers,
            mfa_methods=mfa_methods,
        )

        # AST-enriched path: precise decorator-based auth detection
        if index is not None:
            auth_decorators = [
                "login_required", "UseGuards", "Authorized", "requires_auth",
                "permission_required", "protect", "authenticated",
            ]
            for dec in auth_decorators:
                usages = index.get_decorator_usage(dec)
                for file_path, defn in usages:
                    pattern = f"{defn.name} (via @{dec})"
                    if pattern not in result.protected_route_patterns:
                        result.protected_route_patterns.append(pattern)

            # Detect auth middleware from imports
            auth_modules = [
                "passport", "next-auth", "@auth", "firebase/auth", "clerk",
                "supabase", "auth0", "django.contrib.auth", "flask_login",
            ]
            for mod in auth_modules:
                importers = index.who_imports(mod)
                for imp in importers[:5]:
                    if imp not in result.auth_middleware:
                        result.auth_middleware.append(imp)

        return result

    def _detect_oauth_providers(self, repo_path: Path) -> list[str]:
        """Detect configured OAuth providers from env files and dependencies."""
        providers: list[str] = []
        provider_env_vars: dict[str, list[str]] = {
            "google": ["GOOGLE_CLIENT_ID", "GOOGLE_ID"],
            "github": ["GITHUB_CLIENT_ID", "GITHUB_ID"],
            "microsoft": ["AZURE_AD_CLIENT_ID", "MICROSOFT_CLIENT_ID"],
            "apple": ["APPLE_CLIENT_ID", "APPLE_ID"],
            "facebook": ["FACEBOOK_APP_ID", "FACEBOOK_CLIENT_ID"],
            "discord": ["DISCORD_CLIENT_ID"],
            "twitter": ["TWITTER_CLIENT_ID"],
        }
        for env_file in (".env.example", ".env.local.example", ".env"):
            path = repo_path / env_file
            content = self.read_file(path)
            if content:
                for provider, env_vars in provider_env_vars.items():
                    if any(v in content for v in env_vars):
                        if provider not in providers:
                            providers.append(provider)
        # Also check deps for provider-specific passport strategies
        dep_names = self._collect_dep_names(repo_path)
        dep_providers: dict[str, str] = {
            "passport-google-oauth20": "google",
            "passport-github2": "github",
            "passport-github": "github",
            "passport-facebook": "facebook",
            "passport-twitter": "twitter",
            "passport-discord": "discord",
            "passport-apple": "apple",
        }
        for dep, provider in dep_providers.items():
            if dep in dep_names and provider not in providers:
                providers.append(provider)
        return providers

    def _detect_mfa_methods(self, dep_names: set[str]) -> list[str]:
        """Detect MFA/2FA methods from dependencies."""
        methods: list[str] = []
        totp_libs = ["otplib", "speakeasy", "pyotp", "java-totp", "pquerna/otp"]
        webauthn_libs = [
            "@simplewebauthn/server", "@simplewebauthn/browser",
            "py_webauthn", "go-webauthn",
        ]
        sms_libs = ["twilio", "@vonage/server-sdk", "nexmo"]

        if any(lib in dep_names for lib in totp_libs):
            methods.append("totp")
        if any(lib in dep_names for lib in webauthn_libs):
            methods.append("webauthn")
        if any(lib in dep_names for lib in sms_libs):
            methods.append("sms")
        return methods

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
            # Go auth libs
            "golang-jwt/jwt": "golang-jwt",
            "goth": "goth",
            "go-oidc": "go-oidc",
            "go-webauthn": "go-webauthn",
            # Ruby auth libs
            "devise": "devise",
            "omniauth": "omniauth",
            "sorcery": "sorcery",
            "rodauth": "rodauth",
            "doorkeeper": "doorkeeper",
            # .NET auth libs
            "Microsoft.AspNetCore.Identity": "aspnet-identity",
            "Duende.IdentityServer": "duende-identityserver",
            "Microsoft.Identity.Web": "microsoft-identity-web",
            # Java auth libs
            "spring-boot-starter-security": "spring-security",
            "keycloak-spring-boot-starter": "keycloak",
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

    def _detect_permission_and_protected(
        self, repo_path: Path, dep_names: set[str]
    ) -> tuple[str | None, list[str]]:
        """Single tree pass for permission heuristics and protected-route patterns."""
        permission_model: str | None = None
        if "@casl/ability" in dep_names or "casl" in dep_names:
            permission_model = "abac"

        patterns: list[str] = []
        perm_ext = frozenset({".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".cs", ".rb"})
        prot_ext = frozenset({".ts", ".tsx", ".js", ".jsx", ".py", ".java"})
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

        scan_dir = self._get_scan_root(repo_path)
        perm_files = 0
        prot_files = 0

        for path in scan_dir.rglob("*"):
            permission_done = permission_model is not None or perm_files >= MAX_SOURCE_FILES_AUTH_PERMISSION
            protected_done = prot_files >= MAX_SOURCE_FILES_AUTH_PROTECTED
            if permission_done and protected_done:
                break
            if not path.is_file() or any(s in path.parts for s in SKIP_DIRS):
                continue

            perm_eligible = path.suffix in perm_ext
            prot_eligible = path.suffix in prot_ext
            if not perm_eligible and not prot_eligible:
                continue

            content = self.read_file(path)
            if not content:
                continue

            if (
                permission_model is None
                and perm_eligible
                and perm_files < MAX_SOURCE_FILES_AUTH_PERMISSION
            ):
                perm_files += 1
                for model, indicators in PERMISSION_MODEL_INDICATORS.items():
                    for ind in indicators:
                        if ind in content:
                            permission_model = model
                            break
                    if permission_model:
                        break

            if prot_eligible and prot_files < MAX_SOURCE_FILES_AUTH_PROTECTED:
                prot_files += 1
                for pat in guard_patterns:
                    matches = re.findall(pat, content)
                    if matches:
                        for m in matches:
                            p = m if m else pat.strip("\\()")
                            if p not in patterns:
                                patterns.append(p)

        return permission_model, patterns[:10]

    def _detect_auth_directories(self, repo_path: Path) -> list[str]:
        dirs: list[str] = []
        for d in AUTH_DIRECTORY_PATTERNS:
            if (repo_path / d).is_dir():
                dirs.append(d)
        return dirs


register(AuthAnalyzer())
