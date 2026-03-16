"""Onboarding Guide Generator — generates role-specific onboarding docs.

Produces a markdown onboarding guide for each contributor role that
explains their access scope, blocked commands, and how to get started.
Also generates the bootstrap meta-rule for deep analysis.
"""

from __future__ import annotations

import logging
from pathlib import Path

from product_builders.generators.base import BaseGenerator
from product_builders.generators.cursor_rules import _build_zone_map
from product_builders.generators.registry import register
from product_builders.models.profile import ProductProfile
from product_builders.models.scopes import ContributorRole
from product_builders.profiles.base import DEFAULT_PROFILES

logger = logging.getLogger(__name__)


class OnboardingGenerator(BaseGenerator):
    @property
    def name(self) -> str:
        return "Onboarding Guide Generator"

    def generate(
        self,
        profile: ProductProfile,
        output_dir: Path,
        *,
        role: ContributorRole | None = None,
    ) -> list[Path]:
        generated: list[Path] = []

        if role is None:
            role = ContributorRole.ENGINEER

        # Onboarding guide
        guide_path = self._generate_onboarding(profile, output_dir, role)
        generated.append(guide_path)

        # Bootstrap meta-rule
        bootstrap_path = self._generate_bootstrap(profile, output_dir)
        generated.append(bootstrap_path)

        return generated

    def _generate_onboarding(
        self, profile: ProductProfile, output_dir: Path, role: ContributorRole
    ) -> Path:
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
        }

        content = self.render_template("onboarding-guide.md.j2", **context)
        filename = f"onboarding-{role.value}.md"
        return self.write_file(output_dir / "docs" / filename, content)

    def _generate_bootstrap(self, profile: ProductProfile, output_dir: Path) -> Path:
        content = self.render_template("bootstrap-meta-rule.mdc.j2", profile=profile)
        return self.write_file(
            output_dir / ".cursor" / "rules" / "bootstrap-meta-rule.mdc", content
        )


register(OnboardingGenerator())
