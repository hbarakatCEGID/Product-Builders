from __future__ import annotations

"""Tests for AuthAnalyzer."""
import json
from pathlib import Path

from product_builders.analyzers.auth import AuthAnalyzer


def test_detects_jwt_strategy(tmp_path: Path) -> None:
    pkg = {"dependencies": {"jsonwebtoken": "^9.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    analyzer = AuthAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.auth_strategy == "jwt"


def test_detects_supabase_auth_strategy(tmp_path: Path) -> None:
    pkg = {"dependencies": {"@supabase/supabase-js": "^2.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    analyzer = AuthAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.auth_strategy == "supabase"


def test_detects_auth_middleware(tmp_path: Path) -> None:
    pkg = {"dependencies": {"passport": "^0.7.0", "passport-local": "^1.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    analyzer = AuthAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert "passport" in result.auth_middleware


def test_detects_oauth_providers_from_env(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("GOOGLE_CLIENT_ID=abc123\nSECRET_KEY=xyz\n")

    analyzer = AuthAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert "google" in result.oauth_providers


def test_detects_rbac_permission_model(tmp_path: Path) -> None:
    src = tmp_path / "src"
    guards = src / "guards"
    guards.mkdir(parents=True)
    (guards / "role.ts").write_text(
        "export class RolesGuard {\n"
        "  canActivate(role: string) {\n"
        "    return role === 'admin';\n"
        "  }\n"
        "}\n"
    )

    analyzer = AuthAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.permission_model == "rbac"


def test_detects_protected_route_patterns(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "controller.ts").write_text(
        "import { UseGuards } from '@nestjs/common';\n"
        "@UseGuards(AuthGuard)\n"
        "export class AppController {}\n"
    )

    analyzer = AuthAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert len(result.protected_route_patterns) > 0


def test_empty_repo_no_auth(tmp_path: Path) -> None:
    analyzer = AuthAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.auth_strategy is None
    assert result.status.value == "success"


def test_anti_pattern_no_auth_strategy(tmp_path: Path) -> None:
    analyzer = AuthAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert any("no authentication strategy" in ap for ap in result.anti_patterns)


def test_anti_pattern_no_mfa(tmp_path: Path) -> None:
    pkg = {"dependencies": {"jsonwebtoken": "^9.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    analyzer = AuthAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert result.auth_strategy == "jwt"
    assert any("no MFA" in ap or "no mfa" in ap.lower() for ap in result.anti_patterns)


def test_detects_mfa_totp(tmp_path: Path) -> None:
    pkg = {"dependencies": {"otplib": "^12.0.0", "jsonwebtoken": "^9.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    analyzer = AuthAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert "totp" in result.mfa_methods


def test_detects_supabase_auth_middleware(tmp_path: Path) -> None:
    pkg = {"dependencies": {"@supabase/supabase-js": "^2.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    analyzer = AuthAnalyzer()
    result = analyzer.analyze(tmp_path)

    assert any("supabase" in m for m in result.auth_middleware)


def test_no_js_patterns_in_python_project(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "myapp"\n')
    src = tmp_path / "src"
    src.mkdir()
    # File content mentions "withAuth" and "requireAuth" but this is a Python project
    (src / "views.py").write_text(
        "# Comments referencing JS patterns: withAuth, requireAuth, @UseGuards\n"
        "def my_view(request):\n"
        "    pass\n"
    )

    analyzer = AuthAnalyzer()
    result = analyzer.analyze(tmp_path)

    # Should NOT detect JS patterns like withAuth or UseGuards
    for pat in result.protected_route_patterns:
        assert "UseGuards" not in pat
        assert "withAuth" not in pat
        assert "requireAuth" not in pat
