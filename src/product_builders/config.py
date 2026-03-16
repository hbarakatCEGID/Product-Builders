"""Configuration management for Product Builders.

Handles:
  - Paths to profiles directory, company standards, templates
  - Loading/saving product profiles
  - Loading company standards YAML files
  - Loading overrides per product
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_PACKAGE_DIR = Path(__file__).resolve().parent

# Derive defaults from environment or fall back to source-tree-relative paths.
# When installed as a package, users should set PB_HOME or pass explicit paths.
_DEFAULT_HOME = Path(os.environ.get(
    "PB_HOME",
    str(_PACKAGE_DIR.parent.parent),  # works in source tree; user overrides for installs
))

PROFILES_DIR = Path(os.environ.get("PB_PROFILES_DIR", str(_DEFAULT_HOME / "profiles")))
COMPANY_STANDARDS_DIR = Path(os.environ.get(
    "PB_STANDARDS_DIR",
    str(_DEFAULT_HOME / "company_standards"),
))

_PRODUCT_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


def validate_product_name(name: str) -> str:
    """Validate and sanitize a product name for safe use as a directory name.

    Raises ValueError if the name contains path traversal or invalid characters.
    """
    if not name or not _PRODUCT_NAME_RE.match(name):
        raise ValueError(
            f"Invalid product name '{name}'. "
            "Names must start with alphanumeric and contain only [a-zA-Z0-9._-]."
        )
    if ".." in name:
        raise ValueError(f"Product name must not contain '..': '{name}'")
    return name


class Config:
    """Central configuration for Product Builders operations."""

    def __init__(
        self,
        profiles_dir: Path | None = None,
        company_standards_dir: Path | None = None,
    ) -> None:
        self.profiles_dir = profiles_dir or PROFILES_DIR
        self.company_standards_dir = company_standards_dir or COMPANY_STANDARDS_DIR

    def get_product_dir(self, product_name: str) -> Path:
        """Return the profile directory for a product (validated against traversal)."""
        safe_name = validate_product_name(product_name)
        resolved = (self.profiles_dir / safe_name).resolve()
        if not resolved.is_relative_to(self.profiles_dir.resolve()):
            raise ValueError(f"Product name would escape profiles directory: '{product_name}'")
        return resolved

    def get_analysis_path(self, product_name: str) -> Path:
        return self.get_product_dir(product_name) / "analysis.json"

    def get_scopes_path(self, product_name: str) -> Path:
        return self.get_product_dir(product_name) / "scopes.yaml"

    def get_overrides_path(self, product_name: str) -> Path:
        return self.get_product_dir(product_name) / "overrides.yaml"

    def get_cursor_rules_dir(self, product_name: str) -> Path:
        return self.get_product_dir(product_name) / ".cursor" / "rules"

    def get_prompts_dir(self, product_name: str) -> Path:
        return self.get_product_dir(product_name) / "prompts"

    def list_products(self) -> list[str]:
        """Return names of all analyzed products."""
        if not self.profiles_dir.exists():
            return []
        return sorted(
            d.name
            for d in self.profiles_dir.iterdir()
            if d.is_dir() and (d / "analysis.json").exists()
        )

    def load_company_standards(self) -> dict[str, dict[str, Any]]:
        """Load all company standards YAML files into a dict keyed by filename stem."""
        standards: dict[str, dict[str, Any]] = {}
        if not self.company_standards_dir.exists():
            logger.warning("Company standards directory not found: %s", self.company_standards_dir)
            return standards

        for yaml_file in sorted(self.company_standards_dir.glob("*.yaml")):
            if yaml_file.stem == "schema":
                continue
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    standards[yaml_file.stem] = data
            except Exception as e:
                logger.error("Failed to load standard %s: %s", yaml_file.name, e)

        return standards

    def load_overrides(self, product_name: str) -> dict[str, Any]:
        """Load product-specific overrides, returning empty dict if absent."""
        path = self.get_overrides_path(product_name)
        if not path.exists():
            return {}
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.error("Failed to load overrides for %s: %s", product_name, e)
            return {}
