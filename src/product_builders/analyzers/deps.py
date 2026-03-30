"""Shared dependency-name extraction and package→label maps for analyzers.

Keeps validation / security detection aligned and avoids duplicating
requirements.txt + package.json parsing across modules.
"""

from __future__ import annotations

# Primary language identifiers used for language-filtered detection.
LANG_JAVASCRIPT = "javascript"
LANG_TYPESCRIPT = "typescript"
LANG_PYTHON = "python"
LANG_JAVA = "java"
LANG_RUBY = "ruby"
LANG_GO = "go"
LANG_RUST = "rust"
LANG_CSHARP = "csharp"

# BaaS auth middleware: package name → display label
BAAS_AUTH_MIDDLEWARE: dict[str, str] = {
    "@supabase/ssr": "supabase-ssr",
    "@supabase/auth-helpers-nextjs": "supabase-auth-helpers",
    "@supabase/supabase-js": "supabase-auth",
    "firebase-admin": "firebase-admin-auth",
    "@firebase/auth": "firebase-auth",
    "@clerk/nextjs": "clerk",
    "@auth0/nextjs-auth0": "auth0",
}

# Git remote host → platform name
GIT_REMOTE_HOST_TO_PLATFORM: dict[str, str] = {
    "github.com": "github",
    "gitlab.com": "gitlab",
    "dev.azure.com": "azure-devops",
    "visualstudio.com": "azure-devops",
    "bitbucket.org": "bitbucket",
}

# npm/pip package name → short label (used by Security & API analyzers)
VALIDATION_PACKAGE_TO_NAME: dict[str, str] = {
    "zod": "zod",
    "joi": "joi",
    "yup": "yup",
    "class-validator": "class-validator",
    "ajv": "ajv",
    "express-validator": "express-validator",
    "cerberus": "cerberus",
    "marshmallow": "marshmallow",
    "pydantic": "pydantic",
    "voluptuous": "voluptuous",
    "wtforms": "wtforms",
    "django.forms": "django-forms",
    "FluentValidation": "fluent-validation",
    "valibot": "valibot",
    "@sinclair/typebox": "typebox",
}

SECURITY_MIDDLEWARE_PACKAGE_TO_NAME: dict[str, str] = {
    "helmet": "helmet",
    "csurf": "csurf",
    "cors": "cors",
    "express-rate-limit": "express-rate-limit",
    "django.middleware.security": "django-security-middleware",
    "django.middleware.csrf": "django-csrf",
    "SecurityMiddleware": "django-security-middleware",
    "CsrfViewMiddleware": "django-csrf",
    "spring-security": "spring-security",
}

# Substrings to treat as present when found in pyproject.toml (offline heuristic)
SECURITY_PYPROJECT_HINTS: frozenset[str] = frozenset(
    VALIDATION_PACKAGE_TO_NAME.keys() | SECURITY_MIDDLEWARE_PACKAGE_TO_NAME.keys()
)

API_PYPROJECT_HINTS: frozenset[str] = frozenset({
    "fastapi",
    "flask",
    "django",
    "djangorestframework",
    "graphene",
    "strawberry-graphql",
    "grpcio",
    "pydantic",
    "marshmallow",
})
