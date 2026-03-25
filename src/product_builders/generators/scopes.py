"""Scopes system — auto-detect zones from project structure and generate scopes.yaml.

The scopes.yaml is the single source of truth for contributor access control.
It maps directories to named zones and defines what each contributor role can access.
All three governance layers are generated from it.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from product_builders.analyzers.base import SKIP_DIRS as _SKIP_DIRS
from product_builders.models.profile import ProductProfile
from product_builders.models.scopes import ContributorRole, ContributorScope, ScopeConfig, Zone
from product_builders.profiles.base import DEFAULT_PROFILES

logger = logging.getLogger(__name__)


def build_zone_map(profile: ProductProfile, zone_names: list[str]) -> dict[str, list[str]]:
    """Map contributor zone names to path globs using the profile's :class:`ScopeConfig`."""
    result: dict[str, list[str]] = {}
    for name in zone_names:
        zone = profile.scopes.get_zone(name)
        if zone:
            result[name] = zone.paths
    return result


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
    """Detect zones by scanning repo for known directory patterns.

    Uses a three-tier strategy because many JS/TS projects nest sources
    under ``src/`` while others don't:

    1. Direct check (``repo_root / pattern``) — fastest.
    2. ``src/``-prefixed check (``repo_root / src / pattern``).
    3. Single-walk index lookup — a pre-built ``{dir_name: [paths]}`` map
       avoids repeated recursive globs.
    """
    # Build a directory-name index with one walk (avoids N recursive globs).
    dir_index: dict[str, list[Path]] = {}
    for dirpath in repo_path.rglob("*"):
        if not dirpath.is_dir():
            continue
        if any(part in _SKIP_DIRS for part in dirpath.relative_to(repo_path).parts):
            continue
        dir_index.setdefault(dirpath.name, []).append(dirpath)

    zones: list[Zone] = []
    seen_zone_names: set[str] = set()

    for zone_name, dir_patterns in ZONE_DETECTORS:
        found_paths: list[str] = []
        for pattern in dir_patterns:
            candidate = repo_path / pattern
            if candidate.is_dir():
                found_paths.append(f"{pattern}/**")
                continue
            src_candidate = repo_path / "src" / pattern
            if src_candidate.is_dir():
                found_paths.append(f"src/{pattern}/**")
                continue
            # Index lookup for nested occurrences (e.g., supabase/migrations)
            leaf = Path(pattern).name
            for match in dir_index.get(leaf, []):
                rel = match.relative_to(repo_path)
                found_paths.append(f"{rel}/**")
                break

        if found_paths and zone_name not in seen_zone_names:
            seen_zone_names.add(zone_name)
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
    """Build a :class:`ScopeConfig` from ``repo_path`` layout (and profile for future use).

    Detects zones, adds standard configuration/infrastructure path globs without
    mutating cached :class:`Zone` instances from detection.
    """
    detected = auto_detect_zones(repo_path)
    config_extra = [".env*", "config/**"]
    infra_extra = ["docker*", "Dockerfile", "*.yml", "*.yaml"]

    zones: list[Zone] = []
    for z in detected:
        if z.name == "configuration":
            zones.append(Zone(name=z.name, paths=[*z.paths, *config_extra]))
        elif z.name == "infrastructure":
            zones.append(Zone(name=z.name, paths=[*z.paths, *infra_extra]))
        else:
            zones.append(Zone(name=z.name, paths=list(z.paths)))

    if not any(z.name == "configuration" for z in zones):
        zones.append(Zone(name="configuration", paths=config_extra))

    contributor_scopes = generate_default_scopes(zones)

    return ScopeConfig(zones=zones, contributor_scopes=contributor_scopes)


def save_scopes_yaml(scope_config: ScopeConfig, path: Path) -> None:
    """Write ``scope_config`` to ``path`` as YAML (creates parent directories)."""
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
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise PermissionError(
            f"Cannot create directory for scopes.yaml: {path.parent}"
        ) from e
    try:
        path.write_text(
            yaml.dump(
                data, default_flow_style=False, sort_keys=False, allow_unicode=True
            ),
            encoding="utf-8",
        )
    except OSError as e:
        raise PermissionError(f"Cannot write scopes.yaml: {path}") from e
    logger.info("Wrote scopes.yaml: %s", path)


def load_scopes_yaml(path: Path) -> ScopeConfig:
    """Parse ``path`` into a :class:`ScopeConfig` (strict structure and role validation)."""
    if not path.exists():
        raise FileNotFoundError(f"scopes.yaml not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        raise ValueError("Invalid scopes.yaml: empty file")
    if not isinstance(data, dict):
        raise ValueError(
            f"Invalid scopes.yaml: expected mapping, got {type(data).__name__}"
        )

    zones: list[Zone] = []
    for zone_name, zone_data in data.get("zones", {}).items():
        if not isinstance(zone_data, dict):
            raise ValueError(
                f"Invalid scopes.yaml: zone {zone_name!r} must be a mapping"
            )
        raw_paths = zone_data.get("paths", [])
        if isinstance(raw_paths, list):
            paths = raw_paths
        elif isinstance(raw_paths, str):
            paths = [raw_paths]
        else:
            paths = []
        zones.append(Zone(name=zone_name, paths=paths))

    scopes: list[ContributorScope] = []
    for role_str, scope_data in data.get("contributor_scopes", {}).items():
        if not isinstance(scope_data, dict):
            raise ValueError(
                f"Invalid scopes.yaml: contributor_scopes[{role_str!r}] must be a mapping"
            )
        try:
            role = ContributorRole(role_str)
        except ValueError as e:
            raise ValueError(
                f"Invalid role in scopes.yaml: {role_str!r}"
            ) from e
        scopes.append(
            ContributorScope(
                role=role,
                allowed_zones=scope_data.get("allowed_zones", []),
                read_only_zones=scope_data.get("read_only_zones", []),
                forbidden_zones=scope_data.get("forbidden_zones", []),
            )
        )

    return ScopeConfig(zones=zones, contributor_scopes=scopes)
