"""Cursor Permissions Generator — generates cli.json (Layer 3 governance).

cli.json defines hard filesystem deny rules. Unlike hooks (Layer 2), these
cannot be overridden by the AI — files in denied paths simply cannot be
written to, regardless of the prompt.

This is the strictest enforcement layer.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from product_builders.generators.base import BaseGenerator
from product_builders.generators.registry import register
from product_builders.models.profile import ProductProfile
from product_builders.models.scopes import ContributorRole
from product_builders.profiles.base import DEFAULT_PROFILES

logger = logging.getLogger(__name__)


class CursorPermissionsGenerator(BaseGenerator):
    @property
    def name(self) -> str:
        return "Cursor Permissions Generator"

    def generate(
        self,
        profile: ProductProfile,
        output_dir: Path,
        *,
        role: ContributorRole | None = None,
    ) -> list[Path]:
        if role is None:
            role = ContributorRole.ENGINEER

        prof_def = DEFAULT_PROFILES.get(role)
        if not prof_def or not prof_def.install_scope_hooks:
            logger.info("No cli.json needed for %s role (full access)", role.value)
            return []

        scope = profile.scopes.get_scope(role)
        if scope is None:
            logger.warning("No scope defined for role %s — skipping cli.json", role.value)
            return []

        # Collect all paths that should be hard-denied
        denied_paths: list[str] = profile.scopes.get_denied_paths(role)

        # Also deny read-only zones from writes (Layer 3 blocks writes)
        readonly_paths: list[str] = []
        for zone_name in scope.read_only_zones:
            zone = profile.scopes.get_zone(zone_name)
            if zone:
                readonly_paths.extend(zone.paths)

        # Build cli.json structure
        cli_config: dict[str, object] = {
            "permissions": {
                "deny": {
                    "write": list(dict.fromkeys(denied_paths + readonly_paths)),
                },
            },
            "_meta": {
                "role": role.value,
                "role_display_name": prof_def.display_name,
                "description": (
                    f"Hard filesystem deny rules for {prof_def.display_name} role. "
                    f"Files matching these patterns cannot be created, edited, or deleted."
                ),
            },
        }

        cli_path = output_dir / ".cursor" / "cli.json"
        cli_path.parent.mkdir(parents=True, exist_ok=True)
        cli_path.write_text(
            json.dumps(cli_config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(
            "Generated cli.json with %d denied paths for role %s",
            len(denied_paths) + len(readonly_paths),
            role.value,
        )
        return [cli_path]


register(CursorPermissionsGenerator())
