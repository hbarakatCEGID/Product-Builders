"""Product Builders web application (FastAPI + Jinja2).

Run: uvicorn product_builders.webapp.app:app --reload
Or: python -m product_builders.webapp
"""

from __future__ import annotations

from typing import Any


def create_app() -> Any:
    """Application factory."""
    from product_builders.webapp.app import create_app as _create_app

    return _create_app()


__all__ = ["create_app"]
