"""Comprehensive integration tests for all generators.

Tests each generator end-to-end: construct a ProductProfile, invoke
generate(), and verify the output files exist with correct structure.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from product_builders.generators.cursor_hooks import CursorHooksGenerator
from product_builders.generators.cursor_permissions import CursorPermissionsGenerator
from product_builders.generators.cursor_rules import CursorRulesGenerator
from product_builders.generators.onboarding import OnboardingGenerator
from product_builders.generators.registry import get_all_generators
from product_builders.generators.review_checklist import ReviewChecklistGenerator
from product_builders.models.analysis import (
    DatabaseResult,
    DependencyInfo,
    DependenciesResult,
    TechStackResult,
    FrameworkInfo,
    AuthResult,
    TestingResult,
    ConventionsResult,
    CICDResult,
    DesignUIResult,
    AccessibilityResult,
    APIResult,
    PerformanceResult,
    ErrorHandlingResult,
    StateManagementResult,
    EnvConfigResult,
    I18nResult,
    DirectoryPattern,
    StructureResult,
)
from product_builders.models.profile import ProductMetadata, ProductProfile
from product_builders.models.scopes import (
    ContributorRole,
    ContributorScope,
    ScopeConfig,
    Zone,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_profile() -> ProductProfile:
    """Minimal valid ProductProfile -- only the required ``metadata.name``."""
    return ProductProfile(metadata=ProductMetadata(name="test-project"))


@pytest.fixture
def profile_with_database() -> ProductProfile:
    """Profile with database/ORM data so database.mdc is generated."""
    return ProductProfile(
        metadata=ProductMetadata(name="test-project"),
        database=DatabaseResult(
            orm="prisma",
            database_type="postgres",
            migration_tool="prisma",
        ),
    )


@pytest.fixture
def profile_with_scopes() -> ProductProfile:
    """Profile with zones and scopes for testing hooks/permissions generators."""
    zones = [
        Zone(name="frontend_ui", paths=["src/components/**"]),
        Zone(name="database", paths=["migrations/**", "prisma/**"]),
        Zone(name="api", paths=["src/api/**"]),
    ]
    scopes = [
        ContributorScope(
            role=ContributorRole.DESIGNER,
            allowed_zones=["frontend_ui"],
            read_only_zones=["api"],
            forbidden_zones=["database"],
        ),
        ContributorScope(
            role=ContributorRole.ENGINEER,
            allowed_zones=["frontend_ui", "api", "database"],
            read_only_zones=[],
            forbidden_zones=[],
        ),
    ]
    return ProductProfile(
        metadata=ProductMetadata(name="test-project"),
        scopes=ScopeConfig(zones=zones, contributor_scopes=scopes),
    )


@pytest.fixture
def rich_profile() -> ProductProfile:
    """A feature-rich profile that exercises every generator dimension."""
    zones = [
        Zone(name="frontend_ui", paths=["src/components/**", "src/pages/**"]),
        Zone(name="frontend_logic", paths=["src/hooks/**", "src/store/**"]),
        Zone(name="api", paths=["src/api/**"]),
        Zone(name="backend_logic", paths=["src/services/**"]),
        Zone(name="database", paths=["migrations/**", "prisma/**"]),
        Zone(name="infrastructure", paths=[".github/**", "docker/**"]),
        Zone(name="security", paths=["src/auth/**"]),
        Zone(name="configuration", paths=["config/**"]),
        Zone(name="tests", paths=["tests/**"]),
        Zone(name="fixtures", paths=["tests/fixtures/**"]),
    ]
    scopes = [
        ContributorScope(
            role=ContributorRole.ENGINEER,
            allowed_zones=[
                "frontend_ui", "frontend_logic", "api", "backend_logic",
                "database", "infrastructure", "security", "configuration",
                "tests", "fixtures",
            ],
            read_only_zones=[],
            forbidden_zones=[],
        ),
        ContributorScope(
            role=ContributorRole.DESIGNER,
            allowed_zones=["frontend_ui"],
            read_only_zones=["frontend_logic"],
            forbidden_zones=[
                "api", "backend_logic", "database", "infrastructure",
                "security", "configuration",
            ],
        ),
        ContributorScope(
            role=ContributorRole.QA_TESTER,
            allowed_zones=["tests", "fixtures"],
            read_only_zones=["frontend_ui", "frontend_logic", "api", "backend_logic"],
            forbidden_zones=["database", "infrastructure", "security", "configuration"],
        ),
    ]
    return ProductProfile(
        metadata=ProductMetadata(
            name="acme-webapp",
            description="Full-stack SaaS application",
        ),
        tech_stack=TechStackResult(
            primary_language="TypeScript",
            languages={"TypeScript": 80.0, "Python": 20.0},
            frameworks=[
                FrameworkInfo(name="Next.js", version="14.0", category="web"),
                FrameworkInfo(name="FastAPI", version="0.100", category="api"),
            ],
            build_tools=["turbo"],
            package_managers=["pnpm"],
        ),
        database=DatabaseResult(
            orm="prisma",
            database_type="postgres",
            migration_tool="prisma",
            schema_naming_convention="snake_case",
        ),
        auth=AuthResult(
            auth_strategy="jwt",
            permission_model="rbac",
        ),
        dependencies=DependenciesResult(
            dependencies=[
                DependencyInfo(name="next", version="14.0.0"),
                DependencyInfo(name="react", version="18.0.0"),
                DependencyInfo(name="prisma", version="5.0.0"),
            ],
        ),
        error_handling=ErrorHandlingResult(
            error_strategy="exceptions",
            logging_framework="pino",
        ),
        i18n=I18nResult(i18n_framework="next-intl"),
        state_management=StateManagementResult(state_library="zustand"),
        env_config=EnvConfigResult(config_approach="dotenv", has_docker=True),
        structure=StructureResult(
            key_directories=[
                DirectoryPattern(path="src/components", purpose="UI components"),
                DirectoryPattern(path="src/api", purpose="API routes"),
            ],
        ),
        conventions=ConventionsResult(
            linter="eslint",
            formatter="prettier",
            naming_convention="camelCase",
        ),
        security=SecurityResult(input_validation="zod"),
        testing=TestingResult(
            test_framework="vitest",
            test_runner="vitest",
            e2e_framework="playwright",
        ),
        cicd=CICDResult(platform="github-actions"),
        design_ui=DesignUIResult(
            component_library="shadcn",
            css_methodology="tailwind",
        ),
        accessibility=AccessibilityResult(wcag_level="AA"),
        api=APIResult(api_style="rest"),
        performance=PerformanceResult(
            caching_strategy="redis",
            lazy_loading=True,
            code_splitting=True,
        ),
        scopes=ScopeConfig(zones=zones, contributor_scopes=scopes),
    )


# We need the SecurityResult import used above
from product_builders.models.analysis import SecurityResult  # noqa: E402


# ===================================================================
# 1. CursorRulesGenerator tests
# ===================================================================


class TestCursorRulesGenerator:
    """Integration tests for CursorRulesGenerator."""

    def test_rules_generator_produces_mdc_files(
        self, minimal_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """Generate with a minimal profile; at least some .mdc files should appear."""
        gen = CursorRulesGenerator()
        paths = gen.generate(minimal_profile, tmp_path)

        rules_dir = tmp_path / ".cursor" / "rules"
        mdc_files = list(rules_dir.glob("*.mdc"))
        assert len(mdc_files) > 0, "Expected at least one .mdc file"
        assert len(paths) > 0

    def test_rules_generator_skips_database_when_no_orm(
        self, minimal_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """When database data is empty, database.mdc should NOT be generated."""
        gen = CursorRulesGenerator()
        gen.generate(minimal_profile, tmp_path)

        database_file = tmp_path / ".cursor" / "rules" / "database.mdc"
        assert not database_file.exists(), "database.mdc should be skipped when no ORM"

    def test_rules_generator_includes_database_when_orm_present(
        self, profile_with_database: ProductProfile, tmp_path: Path
    ) -> None:
        """When database.orm is set, database.mdc should be generated."""
        gen = CursorRulesGenerator()
        gen.generate(profile_with_database, tmp_path)

        database_file = tmp_path / ".cursor" / "rules" / "database.mdc"
        assert database_file.exists(), "database.mdc should be generated when ORM is set"

    def test_rules_generator_with_role(
        self, minimal_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """Generate with an explicit role; contributor-guide.mdc should exist."""
        gen = CursorRulesGenerator()
        gen.generate(minimal_profile, tmp_path, role=ContributorRole.ENGINEER)

        guide = tmp_path / ".cursor" / "rules" / "contributor-guide.mdc"
        assert guide.exists(), "contributor-guide.mdc should exist when role is specified"

    def test_rules_generator_all_files_have_frontmatter(
        self, minimal_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """Every generated .mdc file should start with YAML frontmatter ('---')."""
        gen = CursorRulesGenerator()
        gen.generate(minimal_profile, tmp_path)

        rules_dir = tmp_path / ".cursor" / "rules"
        mdc_files = list(rules_dir.glob("*.mdc"))
        assert len(mdc_files) > 0, "Need at least one file to test frontmatter"

        for mdc_file in mdc_files:
            content = mdc_file.read_text(encoding="utf-8")
            assert content.startswith("---"), (
                f"{mdc_file.name} does not start with YAML frontmatter"
            )

    def test_rules_generator_with_company_standards(
        self, minimal_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """Setting company standards should not crash the generator."""
        gen = CursorRulesGenerator()
        gen.set_company_standards({
            "coding": {"max_line_length": 120},
            "testing": {"min_coverage": 80},
        })
        # Should not raise
        paths = gen.generate(minimal_profile, tmp_path)
        assert isinstance(paths, list)

    def test_rules_generator_returns_file_paths(
        self, minimal_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """Returned list should contain Path objects that exist on disk."""
        gen = CursorRulesGenerator()
        paths = gen.generate(minimal_profile, tmp_path)

        assert len(paths) > 0, "Generator should return at least one path"
        for p in paths:
            assert isinstance(p, Path), f"Expected Path, got {type(p)}"
            assert p.exists(), f"Returned path does not exist: {p}"


# ===================================================================
# 2. CursorHooksGenerator tests
# ===================================================================


class TestCursorHooksGenerator:
    """Integration tests for CursorHooksGenerator."""

    def test_hooks_generator_produces_json(
        self, profile_with_scopes: ProductProfile, tmp_path: Path
    ) -> None:
        """Profile with scopes should produce hooks.json for a restricted role."""
        gen = CursorHooksGenerator()
        paths = gen.generate(
            profile_with_scopes, tmp_path, role=ContributorRole.DESIGNER
        )

        hooks_file = tmp_path / ".cursor" / "hooks.json"
        assert hooks_file.exists(), "hooks.json should be created for DESIGNER"
        assert len(paths) == 1

    def test_hooks_generator_valid_json_structure(
        self, profile_with_scopes: ProductProfile, tmp_path: Path
    ) -> None:
        """Hooks output should be valid JSON with a 'hooks' key containing a list."""
        gen = CursorHooksGenerator()
        gen.generate(profile_with_scopes, tmp_path, role=ContributorRole.DESIGNER)

        hooks_file = tmp_path / ".cursor" / "hooks.json"
        data = json.loads(hooks_file.read_text(encoding="utf-8"))
        assert "hooks" in data, "Top-level key 'hooks' missing"
        assert isinstance(data["hooks"], list), "'hooks' should be a list"

    def test_hooks_generator_blocks_readonly_zones(
        self, profile_with_scopes: ProductProfile, tmp_path: Path
    ) -> None:
        """DESIGNER has api as read-only -- should produce a hook with action 'block'."""
        gen = CursorHooksGenerator()
        gen.generate(profile_with_scopes, tmp_path, role=ContributorRole.DESIGNER)

        hooks_file = tmp_path / ".cursor" / "hooks.json"
        data = json.loads(hooks_file.read_text(encoding="utf-8"))
        hooks = data["hooks"]

        block_hooks = [h for h in hooks if h.get("action") == "block"]
        assert len(block_hooks) > 0, "Should have at least one blocking hook"

        # At least one hook should cover the read-only api zone paths
        api_hooks = [
            h for h in block_hooks
            if "src/api/**" in h.get("pathGlobs", [])
        ]
        assert len(api_hooks) > 0, "Should have a blocking hook for the api zone"

    def test_hooks_generator_no_hooks_for_engineer_all_allowed(
        self, profile_with_scopes: ProductProfile, tmp_path: Path
    ) -> None:
        """ENGINEER has full access (install_scope_hooks=False) -- no hooks produced."""
        gen = CursorHooksGenerator()
        paths = gen.generate(
            profile_with_scopes, tmp_path, role=ContributorRole.ENGINEER
        )

        assert paths == [], "ENGINEER should produce no hooks"
        hooks_file = tmp_path / ".cursor" / "hooks.json"
        assert not hooks_file.exists(), "hooks.json should not be created for ENGINEER"

    def test_hooks_generator_includes_shell_commands(
        self, profile_with_scopes: ProductProfile, tmp_path: Path
    ) -> None:
        """DESIGNER has blocked shell commands -- should produce a beforeShellExecution hook."""
        gen = CursorHooksGenerator()
        gen.generate(profile_with_scopes, tmp_path, role=ContributorRole.DESIGNER)

        hooks_file = tmp_path / ".cursor" / "hooks.json"
        data = json.loads(hooks_file.read_text(encoding="utf-8"))
        hooks = data["hooks"]

        shell_hooks = [
            h for h in hooks if h.get("event") == "beforeShellExecution"
        ]
        assert len(shell_hooks) > 0, (
            "DESIGNER should have a beforeShellExecution hook for blocked commands"
        )


# ===================================================================
# 3. CursorPermissionsGenerator tests
# ===================================================================


class TestCursorPermissionsGenerator:
    """Integration tests for CursorPermissionsGenerator."""

    def test_permissions_generator_produces_json(
        self, profile_with_scopes: ProductProfile, tmp_path: Path
    ) -> None:
        """DESIGNER has forbidden zones -- cli.json should be generated."""
        gen = CursorPermissionsGenerator()
        paths = gen.generate(
            profile_with_scopes, tmp_path, role=ContributorRole.DESIGNER
        )

        cli_file = tmp_path / ".cursor" / "cli.json"
        assert cli_file.exists(), "cli.json should be created for DESIGNER"
        assert len(paths) == 1

    def test_permissions_generator_valid_structure(
        self, profile_with_scopes: ProductProfile, tmp_path: Path
    ) -> None:
        """Permissions output should have permissions > deny > write keys."""
        gen = CursorPermissionsGenerator()
        gen.generate(profile_with_scopes, tmp_path, role=ContributorRole.DESIGNER)

        cli_file = tmp_path / ".cursor" / "cli.json"
        data = json.loads(cli_file.read_text(encoding="utf-8"))

        assert "permissions" in data
        assert "deny" in data["permissions"]
        assert "write" in data["permissions"]["deny"]
        assert isinstance(data["permissions"]["deny"]["write"], list)

    def test_permissions_generator_includes_forbidden_paths(
        self, profile_with_scopes: ProductProfile, tmp_path: Path
    ) -> None:
        """Forbidden zone paths should appear in deny.write."""
        gen = CursorPermissionsGenerator()
        gen.generate(profile_with_scopes, tmp_path, role=ContributorRole.DESIGNER)

        cli_file = tmp_path / ".cursor" / "cli.json"
        data = json.loads(cli_file.read_text(encoding="utf-8"))
        denied = data["permissions"]["deny"]["write"]

        # DESIGNER has database as forbidden -- those paths should be denied
        assert "migrations/**" in denied, "migrations/** should be in deny.write"
        assert "prisma/**" in denied, "prisma/** should be in deny.write"

    def test_permissions_generator_no_file_when_no_forbidden(
        self, profile_with_scopes: ProductProfile, tmp_path: Path
    ) -> None:
        """ENGINEER has install_scope_hooks=False -- no cli.json produced."""
        gen = CursorPermissionsGenerator()
        paths = gen.generate(
            profile_with_scopes, tmp_path, role=ContributorRole.ENGINEER
        )

        assert paths == [], "ENGINEER should produce no permissions file"
        cli_file = tmp_path / ".cursor" / "cli.json"
        assert not cli_file.exists(), "cli.json should not be created for ENGINEER"


# ===================================================================
# 4. OnboardingGenerator tests
# ===================================================================


class TestOnboardingGenerator:
    """Integration tests for OnboardingGenerator."""

    def test_onboarding_generator_produces_two_files(
        self, minimal_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """OnboardingGenerator should return exactly 2 paths."""
        gen = OnboardingGenerator()
        paths = gen.generate(minimal_profile, tmp_path, role=ContributorRole.ENGINEER)

        assert len(paths) == 2, f"Expected 2 paths, got {len(paths)}"

    def test_onboarding_generates_role_guide(
        self, minimal_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """Should generate docs/onboarding-engineer.md."""
        gen = OnboardingGenerator()
        gen.generate(minimal_profile, tmp_path, role=ContributorRole.ENGINEER)

        guide = tmp_path / "docs" / "onboarding-engineer.md"
        assert guide.exists(), "onboarding-engineer.md should exist"

    def test_onboarding_generates_bootstrap_rule(
        self, minimal_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """Should generate .cursor/rules/bootstrap-meta-rule.mdc."""
        gen = OnboardingGenerator()
        gen.generate(minimal_profile, tmp_path)

        bootstrap = tmp_path / ".cursor" / "rules" / "bootstrap-meta-rule.mdc"
        assert bootstrap.exists(), "bootstrap-meta-rule.mdc should exist"

    def test_onboarding_guide_contains_role_name(
        self, minimal_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """The guide for ENGINEER should mention 'Engineer' in its content."""
        gen = OnboardingGenerator()
        gen.generate(minimal_profile, tmp_path, role=ContributorRole.ENGINEER)

        guide = tmp_path / "docs" / "onboarding-engineer.md"
        content = guide.read_text(encoding="utf-8")
        assert "Engineer" in content, "Guide should mention the role display name"


# ===================================================================
# 5. ReviewChecklistGenerator tests
# ===================================================================


class TestReviewChecklistGenerator:
    """Integration tests for ReviewChecklistGenerator."""

    def test_checklist_generator_produces_file(
        self, minimal_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """Should generate review-checklist.md."""
        gen = ReviewChecklistGenerator()
        gen.generate(minimal_profile, tmp_path)

        checklist = tmp_path / "review-checklist.md"
        assert checklist.exists(), "review-checklist.md should exist"

    def test_checklist_content_is_markdown(
        self, minimal_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """Checklist content should contain markdown checklist items."""
        gen = ReviewChecklistGenerator()
        gen.generate(minimal_profile, tmp_path)

        checklist = tmp_path / "review-checklist.md"
        content = checklist.read_text(encoding="utf-8")
        # Markdown checklist items: "- [ ]" or "- [x]"
        assert "- [ ]" in content or "- [x]" in content, (
            "Checklist should contain markdown checkbox items"
        )

    def test_checklist_generator_returns_single_path(
        self, minimal_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """Should return a list with exactly 1 Path."""
        gen = ReviewChecklistGenerator()
        paths = gen.generate(minimal_profile, tmp_path)

        assert len(paths) == 1, f"Expected 1 path, got {len(paths)}"
        assert isinstance(paths[0], Path)
        assert paths[0].exists()


# ===================================================================
# 6. Registry tests
# ===================================================================


class TestRegistry:
    """Tests for the generator registry."""

    def test_all_generators_registered(self) -> None:
        """Registry should contain exactly 5 generators."""
        generators = get_all_generators()
        assert len(generators) == 5, (
            f"Expected 5 generators, got {len(generators)}: "
            f"{[g.name for g in generators]}"
        )

    def test_generator_names_unique(self) -> None:
        """All registered generators should have distinct names."""
        generators = get_all_generators()
        names = [g.name for g in generators]
        assert len(names) == len(set(names)), (
            f"Duplicate generator names found: {names}"
        )

    def test_generators_have_name_property(self) -> None:
        """All generators should have a non-empty name property."""
        generators = get_all_generators()
        for gen in generators:
            assert hasattr(gen, "name")
            assert isinstance(gen.name, str)
            assert len(gen.name) > 0, f"Generator {gen!r} has empty name"


# ===================================================================
# 7. Cross-Generator tests
# ===================================================================


class TestCrossGenerator:
    """Tests that run all generators together."""

    def test_all_generators_run_with_minimal_profile(
        self, minimal_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """All 5 generators should run without exception on a minimal profile."""
        generators = get_all_generators()
        assert len(generators) == 5

        all_paths: list[Path] = []
        for gen in generators:
            paths = gen.generate(minimal_profile, tmp_path)
            assert isinstance(paths, list), f"{gen.name} did not return a list"
            all_paths.extend(paths)

        # At least some files should be generated
        assert len(all_paths) > 0, "At least one generator should produce output"

    def test_all_generators_run_with_complete_profile(
        self, rich_profile: ProductProfile, tmp_path: Path
    ) -> None:
        """All generators should run without exception on a feature-rich profile."""
        generators = get_all_generators()
        assert len(generators) == 5

        all_paths: list[Path] = []
        for gen in generators:
            # Use DESIGNER role to exercise hooks and permissions
            paths = gen.generate(rich_profile, tmp_path, role=ContributorRole.DESIGNER)
            assert isinstance(paths, list), f"{gen.name} did not return a list"
            all_paths.extend(paths)

        # With a rich profile and DESIGNER role, we should get many files
        assert len(all_paths) > 5, (
            f"Expected many generated files, got {len(all_paths)}"
        )

        # Verify all returned paths exist
        for p in all_paths:
            assert p.exists(), f"Generated file does not exist: {p}"
