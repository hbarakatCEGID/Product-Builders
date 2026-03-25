"""Contributor profile definitions.

Profiles control two things:
  1. Which rules are emphasized (all profiles get all rules)
  2. What scope is enforced (via hooks.json and cli.json)

Five default profiles are provided. Each product customizes
scopes via scopes.yaml — these profiles define the defaults.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from product_builders.models.scopes import ContributorRole


class ContributorProfile(BaseModel):
    """Defines a contributor's capabilities and restrictions."""

    role: ContributorRole
    display_name: str
    description: str

    install_scope_hooks: bool = True
    emphasized_rules: list[str] = Field(
        default_factory=list,
        description="Rule file stems to emphasize for this profile",
    )

    default_allowed_zones: list[str] = Field(default_factory=list)
    default_read_only_zones: list[str] = Field(default_factory=list)
    default_forbidden_zones: list[str] = Field(default_factory=list)

    blocked_shell_commands: list[str] = Field(
        default_factory=list,
        description="Shell command patterns to block (e.g. 'prisma:migrate', 'rm -rf')",
    )


# ---------------------------------------------------------------------------
# Tool-specific command filtering
# ---------------------------------------------------------------------------

# Mapping: command -> set of dependency names that make the command relevant.
# Commands not in this dict are considered universal (always blocked).
_TOOL_SPECIFIC_COMMANDS: dict[str, frozenset[str]] = {
    "prisma:migrate": frozenset({"prisma", "@prisma/client"}),
    "prisma:db push": frozenset({"prisma", "@prisma/client"}),
    "alembic upgrade": frozenset({"alembic", "sqlalchemy"}),
    "alembic downgrade": frozenset({"alembic", "sqlalchemy"}),
    "flyway migrate": frozenset({"flyway"}),
    "docker build": frozenset({"docker"}),
    "docker push": frozenset({"docker"}),
}


def filter_blocked_commands(
    commands: list[str], detected_deps: set[str]
) -> list[str]:
    """Remove tool-specific blocked commands when the tool isn't in the project.

    Universal safety commands (rm -rf, git push --force, npm publish, etc.)
    are always kept.  Tool-specific commands (prisma:migrate, alembic upgrade)
    are only kept when a related dependency is detected.

    If *detected_deps* is empty, all commands are kept (safe default).
    """
    if not detected_deps:
        return list(commands)

    result: list[str] = []
    for cmd in commands:
        required = _TOOL_SPECIFIC_COMMANDS.get(cmd)
        if required is None:
            # Universal command -- always keep
            result.append(cmd)
        elif required & detected_deps:
            # Tool-specific and tool IS present -- keep
            result.append(cmd)
        # else: tool-specific and tool NOT present -- skip
    return result


# ---------------------------------------------------------------------------
# Default profiles
# ---------------------------------------------------------------------------

ENGINEER = ContributorProfile(
    role=ContributorRole.ENGINEER,
    display_name="Engineer",
    description="Full access to all zones. No scope-check hooks installed.",
    install_scope_hooks=False,
    emphasized_rules=[],
    default_allowed_zones=[
        "frontend_ui", "frontend_logic", "api", "backend_logic",
        "database", "infrastructure", "security", "configuration",
        "tests", "fixtures",
    ],
    default_read_only_zones=[],
    default_forbidden_zones=[],
    blocked_shell_commands=[],
)

TECHNICAL_PM = ContributorProfile(
    role=ContributorRole.TECHNICAL_PM,
    display_name="Technical PM",
    description="Frontend + API access. Backend read-only. Critical ops blocked with helpful messages.",
    install_scope_hooks=True,
    emphasized_rules=[],
    default_allowed_zones=["frontend_ui", "frontend_logic", "api"],
    default_read_only_zones=["backend_logic", "tests"],
    default_forbidden_zones=["database", "infrastructure", "security", "configuration"],
    blocked_shell_commands=[
        "prisma:migrate", "prisma:db push",
        "alembic upgrade", "alembic downgrade",
        "npm publish", "yarn publish",
        "rm -rf",
    ],
)

PRODUCT_MANAGER = ContributorProfile(
    role=ContributorRole.PRODUCT_MANAGER,
    display_name="Product Manager",
    description="Frontend zones writable. Backend/API read-only. Database/infra blocked.",
    install_scope_hooks=True,
    emphasized_rules=[],
    default_allowed_zones=["frontend_ui", "frontend_logic"],
    default_read_only_zones=["api", "backend_logic"],
    default_forbidden_zones=["database", "infrastructure", "security", "configuration"],
    blocked_shell_commands=[
        "prisma:migrate", "prisma:db push",
        "alembic upgrade", "alembic downgrade",
        "flyway migrate",
        "npm publish", "yarn publish",
        "docker build", "docker push",
        "rm -rf",
        "git push --force", "git push -f",
        "git reset --hard",
    ],
)

DESIGNER = ContributorProfile(
    role=ContributorRole.DESIGNER,
    display_name="Designer",
    description="UI components and styles only. Strictest permissions.",
    install_scope_hooks=True,
    emphasized_rules=["design-system", "accessibility", "i18n"],
    default_allowed_zones=["frontend_ui"],
    default_read_only_zones=["frontend_logic"],
    default_forbidden_zones=[
        "api", "backend_logic", "database", "infrastructure",
        "security", "configuration",
    ],
    blocked_shell_commands=[
        "prisma:migrate", "prisma:db push",
        "alembic upgrade", "alembic downgrade",
        "npm publish", "yarn publish",
        "docker build", "docker push",
        "rm -rf",
        "git push --force", "git push -f",
        "git reset --hard",
    ],
)

QA_TESTER = ContributorProfile(
    role=ContributorRole.QA_TESTER,
    display_name="QA / Tester",
    description="Test directories and fixtures writable. Cannot modify production code.",
    install_scope_hooks=True,
    emphasized_rules=["testing"],
    default_allowed_zones=["tests", "fixtures"],
    default_read_only_zones=["frontend_ui", "frontend_logic", "api", "backend_logic"],
    default_forbidden_zones=["database", "infrastructure", "security", "configuration"],
    blocked_shell_commands=[
        "prisma:migrate", "prisma:db push",
        "alembic upgrade", "alembic downgrade",
        "npm publish", "yarn publish",
        "docker build", "docker push",
        "rm -rf",
    ],
)

DEFAULT_PROFILES: dict[ContributorRole, ContributorProfile] = {
    ContributorRole.ENGINEER: ENGINEER,
    ContributorRole.TECHNICAL_PM: TECHNICAL_PM,
    ContributorRole.PRODUCT_MANAGER: PRODUCT_MANAGER,
    ContributorRole.DESIGNER: DESIGNER,
    ContributorRole.QA_TESTER: QA_TESTER,
}

ROLE_ALIASES: dict[str, ContributorRole] = {
    "engineer": ContributorRole.ENGINEER,
    "eng": ContributorRole.ENGINEER,
    "technical_pm": ContributorRole.TECHNICAL_PM,
    "tech_pm": ContributorRole.TECHNICAL_PM,
    "technical-pm": ContributorRole.TECHNICAL_PM,
    "product_manager": ContributorRole.PRODUCT_MANAGER,
    "pm": ContributorRole.PRODUCT_MANAGER,
    "designer": ContributorRole.DESIGNER,
    "qa_tester": ContributorRole.QA_TESTER,
    "qa": ContributorRole.QA_TESTER,
    "tester": ContributorRole.QA_TESTER,
}


def resolve_role(alias: str) -> ContributorRole:
    """Resolve a role alias (e.g. 'pm') to a ContributorRole enum."""
    normalized = alias.lower().strip()
    role = ROLE_ALIASES.get(normalized)
    if role is None:
        valid = ", ".join(sorted(ROLE_ALIASES.keys()))
        raise ValueError(f"Unknown contributor role '{alias}'. Valid roles: {valid}")
    return role


def get_profile(role: ContributorRole) -> ContributorProfile:
    """Get the default profile for a contributor role."""
    return DEFAULT_PROFILES[role]
