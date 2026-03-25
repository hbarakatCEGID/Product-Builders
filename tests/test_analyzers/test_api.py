from __future__ import annotations

"""Tests for API analyzer Next.js App Router detection."""
import json
from pathlib import Path
from product_builders.analyzers.api import APIAnalyzer


def test_detects_nextjs_app_router_as_rest(tmp_path: Path) -> None:
    """Next.js with app/api/ routes should detect api_style as rest."""
    pkg = {"dependencies": {"next": "^15"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    (tmp_path / "src" / "app" / "api" / "users").mkdir(parents=True)
    (tmp_path / "src" / "app" / "api" / "users" / "route.ts").write_text(
        "export async function GET() { return Response.json({}) }"
    )
    analyzer = APIAnalyzer()
    result = analyzer.analyze(tmp_path)
    assert result.api_style == "rest"
