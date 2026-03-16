"""Base class for all output generators.

Generators transform a ProductProfile into specific output artifacts:
  - Cursor rule files (.mdc)
  - hooks.json
  - cli.json
  - Onboarding guides
  - Review checklists
  - Team Rules recommendations

All generators use Jinja2 templates stored in generators/templates/.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from product_builders.models.profile import ProductProfile
from product_builders.models.scopes import ContributorRole

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


class BaseGenerator(ABC):
    """Abstract base class for output generators."""

    def __init__(self) -> None:
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "htm", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name (e.g. 'Cursor Rules Generator')."""

    @abstractmethod
    def generate(
        self,
        profile: ProductProfile,
        output_dir: Path,
        *,
        role: ContributorRole | None = None,
    ) -> list[Path]:
        """Generate output files from a product profile.

        Args:
            profile: The analyzed product profile.
            output_dir: Directory to write generated files to.
            role: Optional contributor role for role-specific output.

        Returns:
            List of paths to generated files.
        """

    def render_template(self, template_name: str, **context: object) -> str:
        """Render a Jinja2 template with the given context."""
        template = self._jinja_env.get_template(template_name)
        return template.render(**context)

    def write_file(self, path: Path, content: str) -> Path:
        """Write content to a file, creating parent directories as needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info("Generated: %s", path)
        return path
