"""Scopes system — auto-detect zones from project structure and generate scopes.yaml.

The scopes.yaml is the single source of truth for contributor access control.
It maps directories to named zones and defines what each contributor role can access.
All three governance layers are generated from it.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from product_builders.models.profile import ProductProfile
from product_builders.models.scopes import ContributorRole, ContributorScope, ScopeConfig, Zone
from product_builders.profiles.base import DEFAULT_PROFILES

logger = logging.getLogger(__name__)

# Zone auto-detection: directory patterns → zone name
ZONE_DETECTORS: list[tuple[str, list[str]]] = [
    ("frontend_ui", [
        "src/components", "src/pages", "src/views", "src/styles", "src/css",
        "public", "static", "app/components", "app/pages", "app/views",
        "components", "pages", "views",
    ]),
    ("frontend_logic", [
        "src/hooks", "src/utils/client", "src/store", "src/redux",
        "src/context", "src/state", "src/lib/client",
        "app/hooks", "app/store",
    ]),
    ("api", [
        "src/api", "src/routes", "src/controllers", "src/endpoints",
        "app/api", "app/routes", "app/controllers",
        "routes", "controllers", "api",
    ]),
    ("backend_logic", [
        "src/services", "src/lib", "src/domain", "src/logic",
        "app/services", "app/lib", "lib", "services",
    ]),
    ("database", [
        "migrations", "prisma", "src/models", "src/entities",
        "db/migrate", "alembic", "src/database",
        "app/models", "models",
    ]),
    ("infrastructure", [
        ".github", ".gitlab", ".circleci", "docker",
        "deploy", "infra", "terraform", "k8s", "helm",
    ]),
    ("security", [
        "src/auth", "src/authentication", "src/middleware/auth",
        "src/guards", "app/auth", "auth",
    ]),
    ("configuration", [
        "config", "conf",
    ]),
    ("tests", [
        "tests", "test", "__tests__", "spec", "specs",
        "src/__tests__", "src/test",
    ]),
    ("fixtures", [
        "tests/fixtures", "tests/data", "test/fixtures",
        "fixtures", "seeds", "db/seeds",
    ]),
]


def auto_detect_zones(repo_path: Path) -> list[Zone]:
    """Auto-detect zones from project directory structure."""
    zones: list[Zone] = []

    for zone_name, dir_patterns in ZONE_DETECTORS:
        found_paths: list[str] = []
        for pattern in dir_patterns:
            if (repo_path / pattern).is_dir():
                found_paths.append(f"{pattern}/**")

        if found_paths:
            zones.append(Zone(name=zone_name, paths=found_paths))

    return zones


def generate_default_scopes(zones: list[Zone]) -> list[ContributorScope]:
    """Generate default contributor scopes from detected zones."""
    zone_names = {z.name for z in zones}
    scopes: list[ContributorScope] = []

    for role, profile_def in DEFAULT_PROFILES.items():
        allowed = [z for z in profile_def.default_allowed_zones if z in zone_names]
        readonly = [z for z in profile_def.default_read_only_zones if z in zone_names]
        forbidden = [z for z in profile_def.default_forbidden_zones if z in zone_names]

        scopes.append(ContributorScope(
            role=role,
            allowed_zones=allowed,
            read_only_zones=readonly,
            forbidden_zones=forbidden,
        ))

    return scopes


def generate_scope_config(profile: ProductProfile, repo_path: Path) -> ScopeConfig:
    """Generate a complete ScopeConfig from analysis results and directory structure."""
    zones = auto_detect_zones(repo_path)

    # Add .env* and docker* to configuration and infrastructure if not already present
    config_zone = next((z for z in zones if z.name == "configuration"), None)
    if config_zone:
        config_zone.paths.extend([".env*", "config/**"])
    else:
        zones.append(Zone(name="configuration", paths=[".env*", "config/**"]))

    infra_zone = next((z for z in zones if z.name == "infrastructure"), None)
    if infra_zone:
        infra_zone.paths.extend(["docker*", "Dockerfile", "*.yml", "*.yaml"])

    contributor_scopes = generate_default_scopes(zones)

    return ScopeConfig(zones=zones, contributor_scopes=contributor_scopes)


def save_scopes_yaml(scope_config: ScopeConfig, path: Path) -> None:
    """Serialize ScopeConfig to scopes.yaml."""
    data = {
        "zones": {
            zone.name: {"paths": zone.paths}
            for zone in scope_config.zones
        },
        "contributor_scopes": {
            scope.role.value: {
                "allowed_zones": scope.allowed_zones,
                "read_only_zones": scope.read_only_zones,
                "forbidden_zones": scope.forbidden_zones,
            }
            for scope in scope_config.contributor_scopes
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    logger.info("Wrote scopes.yaml: %s", path)


def load_scopes_yaml(path: Path) -> ScopeConfig:
    """Load ScopeConfig from a scopes.yaml file."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid scopes.yaml: expected mapping, got {type(data).__name__}")

    zones: list[Zone] = []
    for zone_name, zone_data in data.get("zones", {}).items():
        zones.append(Zone(name=zone_name, paths=zone_data.get("paths", [])))

    scopes: list[ContributorScope] = []
    for role_str, scope_data in data.get("contributor_scopes", {}).items():
        scopes.append(ContributorScope(
            role=ContributorRole(role_str),
            allowed_zones=scope_data.get("allowed_zones", []),
            read_only_zones=scope_data.get("read_only_zones", []),
            forbidden_zones=scope_data.get("forbidden_zones", []),
        ))

    return ScopeConfig(zones=zones, contributor_scopes=scopes)
