"""Cursor Rules Generator — generates 14 .mdc rule files from templates.

Each .mdc file is a Cursor Rule that provides AI assistants with
product-specific context and constraints. The rules are rendered
from Jinja2 templates using data from the ProductProfile.
"""

from __future__ import annotations

import logging
from pathlib import Path

from product_builders.generators.base import BaseGenerator
from product_builders.generators.registry import register
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
    ("testing.mdc.j2", "testing.mdc"),
    ("git-workflow.mdc.j2", "git-workflow.mdc"),
    ("design-system.mdc.j2", "design-system.mdc"),
    ("accessibility.mdc.j2", "accessibility.mdc"),
    ("security.mdc.j2", "security.mdc"),
    ("api-patterns.mdc.j2", "api-patterns.mdc"),
    ("i18n.mdc.j2", "i18n.mdc"),
    ("performance.mdc.j2", "performance.mdc"),
    ("contributor-guide.mdc.j2", "contributor-guide.mdc"),
]


def _should_generate(template_name: str, profile: ProductProfile) -> bool:
    """Skip templates when the relevant analysis dimension has no meaningful data."""
    checks: dict[str, bool] = {
        "database.mdc.j2": profile.database.orm is not None or profile.database.database_type is not None,
        "auth-patterns.mdc.j2": profile.auth.auth_strategy is not None or bool(profile.auth.auth_directories),
        "testing.mdc.j2": profile.testing.test_framework is not None,
        "design-system.mdc.j2": profile.design_ui.component_library is not None or profile.design_ui.css_methodology is not None,
        "accessibility.mdc.j2": profile.accessibility.wcag_level is not None or profile.accessibility.aria_usage_detected,
        "api-patterns.mdc.j2": profile.api.api_style is not None,
        "i18n.mdc.j2": profile.i18n.i18n_framework is not None,
        "performance.mdc.j2": (
            profile.performance.caching_strategy is not None
            or profile.performance.lazy_loading
            or profile.performance.code_splitting
        ),
    }
    return checks.get(template_name, True)


def _build_zone_map(
    profile: ProductProfile, zone_names: list[str]
) -> dict[str, list[str]]:
    """Build a zone_name → paths mapping for the given zone names."""
    result: dict[str, list[str]] = {}
    for name in zone_names:
        zone = profile.scopes.get_zone(name)
        if zone:
            result[name] = zone.paths
    return result


class CursorRulesGenerator(BaseGenerator):
    @property
    def name(self) -> str:
        return "Cursor Rules Generator"

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

            # Contributor guide is role-specific
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
        scope = profile.scopes.get_scope(role)

        writable_zones: dict[str, list[str]] = {}
        readonly_zones: dict[str, list[str]] = {}
        forbidden_zones: dict[str, list[str]] = {}

        if scope:
            writable_zones = _build_zone_map(profile, scope.allowed_zones)
            readonly_zones = _build_zone_map(profile, scope.read_only_zones)
            forbidden_zones = _build_zone_map(profile, scope.forbidden_zones)

        context = {
            "profile": profile,
            "role": role.value,
            "role_display_name": prof_def.display_name if prof_def else role.value,
            "writable_zones": writable_zones,
            "readonly_zones": readonly_zones,
            "forbidden_zones": forbidden_zones,
            "blocked_commands": prof_def.blocked_shell_commands if prof_def else [],
            "emphasized_rules": prof_def.emphasized_rules if prof_def else [],
        }

        content = self.render_template("contributor-guide.mdc.j2", **context)
        path = self.write_file(rules_dir / "contributor-guide.mdc", content)
        return [path]

    def _build_context(
        self, profile: ProductProfile, role: ContributorRole | None
    ) -> dict[str, object]:
        """Build template context with profile and role info."""
        ctx: dict[str, object] = {"profile": profile}

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
