"""Cursor Rules Generator — generates .mdc rule files from templates.

Each .mdc file is a Cursor Rule that provides AI assistants with
product-specific context and constraints. The rules are rendered
from Jinja2 templates using data from the ProductProfile.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from product_builders.generators.base import BaseGenerator
from product_builders.generators.registry import register
from product_builders.generators.scopes import build_role_zone_context
from product_builders.models.profile import ProductProfile
from product_builders.models.scopes import ContributorRole
from product_builders.profiles.base import DEFAULT_PROFILES

logger = logging.getLogger(__name__)

# Template name → output filename
# Ordered by priority (highest first) to match Cursor's rule resolution
RULE_TEMPLATES: list[tuple[str, str]] = [
    ("project-overview.mdc.j2", "project-overview.mdc"),
    ("tech-stack.mdc.j2", "tech-stack.mdc"),
    ("database.mdc.j2", "database.mdc"),
    ("auth-patterns.mdc.j2", "auth-patterns.mdc"),
    ("error-handling.mdc.j2", "error-handling.mdc"),
    ("architecture.mdc.j2", "architecture.mdc"),
    ("coding-conventions.mdc.j2", "coding-conventions.mdc"),
    ("dependencies.mdc.j2", "dependencies.mdc"),
    ("testing.mdc.j2", "testing.mdc"),
    ("git-workflow.mdc.j2", "git-workflow.mdc"),
    ("design-system.mdc.j2", "design-system.mdc"),
    ("accessibility.mdc.j2", "accessibility.mdc"),
    ("security.mdc.j2", "security.mdc"),
    ("api-patterns.mdc.j2", "api-patterns.mdc"),
    ("i18n.mdc.j2", "i18n.mdc"),
    ("state-and-config.mdc.j2", "state-and-config.mdc"),
    ("frontend-patterns.mdc.j2", "frontend-patterns.mdc"),
    ("user-flows.mdc.j2", "user-flows.mdc"),
    ("performance.mdc.j2", "performance.mdc"),
    ("cicd.mdc.j2", "cicd.mdc"),
    ("contributor-guide.mdc.j2", "contributor-guide.mdc"),
]


def _should_generate(template_name: str, profile: ProductProfile) -> bool:
    """Skip templates when the relevant analysis dimension has no meaningful data."""
    checks: dict[str, bool] = {
        "database.mdc.j2": (
            profile.database.orm is not None
            or profile.database.database_type is not None
            or bool(profile.domain_model_deep.entity_relationships)
        ),
        "auth-patterns.mdc.j2": profile.auth.auth_strategy is not None,
        "architecture.mdc.j2": (
            profile.architecture_deep.layering_pattern is not None
            or bool(profile.architecture_deep.module_boundaries)
            or bool(profile.structure.key_directories)
        ),
        "coding-conventions.mdc.j2": (
            profile.conventions.linter is not None
            or profile.conventions.formatter is not None
            or profile.conventions.naming_convention is not None
            or profile.implicit_conventions_deep.naming_philosophy is not None
        ),
        "testing.mdc.j2": profile.testing.test_framework is not None,
        "design-system.mdc.j2": profile.design_ui.component_library is not None or profile.design_ui.css_methodology is not None,
        "accessibility.mdc.j2": (
            profile.accessibility.wcag_level is not None
            or bool(profile.accessibility.a11y_testing_tools)
        ),
        "api-patterns.mdc.j2": profile.api.api_style is not None,
        "i18n.mdc.j2": profile.i18n.i18n_framework is not None,
        "state-and-config.mdc.j2": (
            profile.state_management.state_library is not None
            or bool(profile.state_management.state_patterns)
            or profile.env_config.config_approach is not None
            or profile.env_config.has_docker
        ),
        "error-handling.mdc.j2": (
            profile.error_handling.error_strategy is not None
            or profile.error_handling.logging_framework is not None
            or profile.implicit_conventions_deep.error_handling_philosophy is not None
        ),
        "frontend-patterns.mdc.j2": (
            bool(profile.frontend_patterns.layout_patterns)
            or bool(profile.frontend_patterns.form_libraries)
            or bool(profile.frontend_patterns.loading_patterns)
            or profile.frontend_patterns.modal_pattern is not None
            or profile.frontend_patterns.routing_library is not None
        ),
        "user-flows.mdc.j2": (
            profile.user_flows.route_count > 0
            or bool(profile.user_flows.route_files)
        ),
        "performance.mdc.j2": (
            profile.performance.caching_strategy is not None
            or profile.performance.lazy_loading
            or profile.performance.code_splitting
        ),
        "dependencies.mdc.j2": bool(profile.dependencies.dependencies),
        "cicd.mdc.j2": profile.cicd.platform is not None,
    }
    return checks.get(template_name, True)


class CursorRulesGenerator(BaseGenerator):
    def __init__(self) -> None:
        super().__init__()
        self._company_standards: dict[str, dict[str, Any]] = {}

    @property
    def name(self) -> str:
        return "Cursor Rules Generator"

    def set_company_standards(self, standards: dict[str, dict[str, Any]]) -> None:
        """Inject loaded company standards for merging into generated rules."""
        self._company_standards = standards

    def generate(
        self,
        profile: ProductProfile,
        output_dir: Path,
        *,
        role: ContributorRole | None = None,
    ) -> list[Path]:
        rules_dir = output_dir / ".cursor" / "rules"
        generated: list[Path] = []

        for template_name, output_name in RULE_TEMPLATES:
            if not _should_generate(template_name, profile):
                logger.info("Skipping %s (no relevant data)", output_name)
                continue

            if template_name == "contributor-guide.mdc.j2":
                if role is None:
                    role = ContributorRole.ENGINEER
                generated.extend(
                    self._generate_contributor_guide(profile, rules_dir, role)
                )
                continue

            context = self._build_context(profile, role)
            content = self.render_template(template_name, **context)
            path = self.write_file(rules_dir / output_name, content)
            generated.append(path)

        return generated

    def _generate_contributor_guide(
        self,
        profile: ProductProfile,
        rules_dir: Path,
        role: ContributorRole,
    ) -> list[Path]:
        """Generate role-specific contributor guide."""
        prof_def = DEFAULT_PROFILES.get(role)
        zones = build_role_zone_context(profile, role)

        context = {
            "profile": profile,
            "role": role.value,
            "role_display_name": prof_def.display_name if prof_def else role.value,
            **zones,
            "blocked_commands": prof_def.blocked_shell_commands if prof_def else [],
            "emphasized_rules": prof_def.emphasized_rules if prof_def else [],
        }

        content = self.render_template("contributor-guide.mdc.j2", **context)
        path = self.write_file(rules_dir / "contributor-guide.mdc", content)
        return [path]

    def _build_context(
        self, profile: ProductProfile, role: ContributorRole | None
    ) -> dict[str, object]:
        """Build template context with profile, role, and company standards."""
        ctx: dict[str, object] = {
            "profile": profile,
            "company_standards": self._company_standards,
        }

        if role:
            prof_def = DEFAULT_PROFILES.get(role)
            scope = profile.scopes.get_scope(role)
            ctx["role"] = role.value
            ctx["role_display_name"] = prof_def.display_name if prof_def else role.value

            if scope:
                ctx["writable_summary"] = scope.allowed_zones
                ctx["readonly_summary"] = scope.read_only_zones
                ctx["forbidden_summary"] = scope.forbidden_zones

        return ctx


register(CursorRulesGenerator())
