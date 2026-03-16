"""Scope and zone models for contributor access control.

A single scopes.yaml drives all three enforcement layers:
  Layer 1 (rules) - soft guidance in contributor-guide.mdc
  Layer 2 (hooks) - smart blocking via hooks.json
  Layer 3 (permissions) - hard deny via cli.json
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ContributorRole(str, Enum):
    ENGINEER = "engineer"
    TECHNICAL_PM = "technical_pm"
    PRODUCT_MANAGER = "product_manager"
    DESIGNER = "designer"
    QA_TESTER = "qa_tester"


class Zone(BaseModel):
    """A named directory zone in the project (e.g. 'frontend_ui')."""

    name: str = Field(min_length=1)
    paths: list[str] = Field(
        description="Glob patterns relative to project root (e.g. 'src/components/**')"
    )


class ContributorScope(BaseModel):
    """Defines what a contributor role can access."""

    role: ContributorRole
    allowed_zones: list[str] = Field(
        default_factory=list,
        description="Zone names where the contributor can read and write",
    )
    read_only_zones: list[str] = Field(
        default_factory=list,
        description="Zone names where the contributor can read but not write",
    )
    forbidden_zones: list[str] = Field(
        default_factory=list,
        description="Zone names the contributor cannot access at all",
    )


class ScopeConfig(BaseModel):
    """Full scope configuration for a product — parsed from scopes.yaml."""

    zones: list[Zone] = Field(default_factory=list)
    contributor_scopes: list[ContributorScope] = Field(default_factory=list)

    def get_zone(self, name: str) -> Zone | None:
        return next((z for z in self.zones if z.name == name), None)

    def get_scope(self, role: ContributorRole) -> ContributorScope | None:
        return next((s for s in self.contributor_scopes if s.role == role), None)

    def get_writable_paths(self, role: ContributorRole) -> list[str]:
        """Return all glob patterns writable by a role."""
        scope = self.get_scope(role)
        if scope is None:
            return []
        paths: list[str] = []
        for zone_name in scope.allowed_zones:
            zone = self.get_zone(zone_name)
            if zone:
                paths.extend(zone.paths)
        return paths

    def get_readable_paths(self, role: ContributorRole) -> list[str]:
        """Return all glob patterns readable by a role (allowed + read-only)."""
        scope = self.get_scope(role)
        if scope is None:
            return []
        paths: list[str] = []
        for zone_name in scope.allowed_zones + scope.read_only_zones:
            zone = self.get_zone(zone_name)
            if zone:
                paths.extend(zone.paths)
        return paths

    def get_denied_paths(self, role: ContributorRole) -> list[str]:
        """Return all glob patterns denied to a role."""
        scope = self.get_scope(role)
        if scope is None:
            return []
        paths: list[str] = []
        for zone_name in scope.forbidden_zones:
            zone = self.get_zone(zone_name)
            if zone:
                paths.extend(zone.paths)
        return paths
