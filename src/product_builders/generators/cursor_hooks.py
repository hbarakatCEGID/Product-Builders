"""Cursor Hooks Generator — generates hooks.json (Layer 2 governance).

hooks.json provides smart blocking with helpful messages. When a contributor
attempts an action outside their scope, the hook fires and explains why the
action is blocked and what to do instead.

Two hook types:
  - preToolUse: fires before file operations (edit, create, delete)
  - beforeShellExecution: fires before shell commands
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

_ZONE_FRIENDLY_NAMES: dict[str, str] = {
    "frontend_ui": "UI components and styles",
    "frontend_logic": "frontend application logic",
    "api": "API endpoints and routes",
    "backend_logic": "backend services and business logic",
    "database": "database schemas and migrations",
    "infrastructure": "infrastructure and deployment configs",
    "security": "authentication and security code",
    "configuration": "configuration files",
    "tests": "test files",
    "fixtures": "test fixtures and seed data",
}


def _zone_description(zone_name: str) -> str:
    return _ZONE_FRIENDLY_NAMES.get(zone_name, zone_name)


class CursorHooksGenerator(BaseGenerator):
    @property
    def name(self) -> str:
        return "Cursor Hooks Generator"

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
            logger.info("No hooks needed for %s role", role.value)
            return []

        scope = profile.scopes.get_scope(role)
        if scope is None:
            logger.warning("No scope defined for role %s — skipping hooks", role.value)
            return []

        hooks: list[dict[str, object]] = []

        # preToolUse hooks for read-only zones
        for zone_name in scope.read_only_zones:
            zone = profile.scopes.get_zone(zone_name)
            if not zone:
                continue
            hooks.append({
                "event": "preToolUse",
                "tools": ["edit_file", "create_file"],
                "pathGlobs": zone.paths,
                "message": (
                    f"⚠️ This file is in the **{_zone_description(zone_name)}** zone, "
                    f"which is read-only for your role ({prof_def.display_name}). "
                    f"You can view this code for context but cannot modify it. "
                    f"If changes are needed, create a task for the engineering team."
                ),
                "action": "block",
            })

        # preToolUse hooks for forbidden zones
        for zone_name in scope.forbidden_zones:
            zone = profile.scopes.get_zone(zone_name)
            if not zone:
                continue
            hooks.append({
                "event": "preToolUse",
                "tools": ["edit_file", "create_file", "delete_file"],
                "pathGlobs": zone.paths,
                "message": (
                    f"🚫 This file is in the **{_zone_description(zone_name)}** zone, "
                    f"which is restricted for your role ({prof_def.display_name}). "
                    f"This area requires engineering team involvement. "
                    f"Please create a Jira/Linear task describing the change you need."
                ),
                "action": "block",
            })

        # beforeShellExecution hooks for blocked commands
        if prof_def.blocked_shell_commands:
            hooks.append({
                "event": "beforeShellExecution",
                "commandPatterns": prof_def.blocked_shell_commands,
                "message": (
                    f"🚫 This command is restricted for your role ({prof_def.display_name}). "
                    f"These operations can affect production data or deployment. "
                    f"Please ask the engineering team to run this command."
                ),
                "action": "block",
            })

        hooks_path = output_dir / ".cursor" / "hooks.json"
        hooks_path.parent.mkdir(parents=True, exist_ok=True)
        hooks_path.write_text(
            json.dumps({"hooks": hooks}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Generated hooks.json with %d hooks for role %s", len(hooks), role.value)
        return [hooks_path]


register(CursorHooksGenerator())
