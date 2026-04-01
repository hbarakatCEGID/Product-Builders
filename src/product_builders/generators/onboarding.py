"""Onboarding Guide Generator — generates role-specific onboarding docs.

Produces a markdown onboarding guide for each contributor role that
explains their access scope, blocked commands, and how to get started.
Also generates the bootstrap meta-rule for deep analysis.
"""

from __future__ import annotations

import logging
from pathlib import Path

from product_builders.generators.base import BaseGenerator
from product_builders.generators.registry import register
from product_builders.generators.scopes import build_role_zone_context
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
        zones = build_role_zone_context(profile, role)

        context = {
            "profile": profile,
            "role": role.value,
            "role_display_name": prof_def.display_name if prof_def else role.value,
            **zones,
            "blocked_commands": prof_def.blocked_shell_commands if prof_def else [],
        }

        content = self.render_template("onboarding-guide.md.j2", **context)
        filename = f"onboarding-{role.value}.md"
        return self.write_file(output_dir / "docs" / filename, content)

    def _generate_bootstrap(self, profile: ProductProfile, output_dir: Path) -> Path:
        from product_builders.deep_analysis.prompts import (
            build_adaptive_questions,
            build_gap_aware_questions,
            get_output_yaml_example,
        )

        content = self.render_template(
            "bootstrap-meta-rule.mdc.j2",
            profile=profile,
            adaptive_questions=build_adaptive_questions(profile),
            gap_questions=build_gap_aware_questions(profile),
            yaml_example=get_output_yaml_example(profile),
        )
        return self.write_file(
            output_dir / ".cursor" / "rules" / "bootstrap-meta-rule.mdc", content
        )


register(OnboardingGenerator())
