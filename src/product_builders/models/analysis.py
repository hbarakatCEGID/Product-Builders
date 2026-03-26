"""Analysis result models for heuristic dimensions (core + extended).

Each model captures the output of one analyzer. Together they form
the ProductProfile — the intermediate representation from which
Cursor rules, hooks, and permissions are generated.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalysisStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"
    SKIPPED = "skipped"


class AnalysisResult(BaseModel):
    """Base for all analyzer outputs."""

    status: AnalysisStatus = AnalysisStatus.SUCCESS
    error_message: str | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    anti_patterns: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# CRITICAL — Can cause data loss or security breaches
# ---------------------------------------------------------------------------


class FrameworkInfo(BaseModel):
    name: str = Field(min_length=1)
    version: str | None = None
    category: str = ""  # e.g. "web", "orm", "testing"


class TechStackResult(AnalysisResult):
    """Dimension 1: Languages, frameworks, build tools, runtime versions."""

    languages: dict[str, float] = Field(
        default_factory=dict,
        description="Language name → percentage of codebase",
    )
    primary_language: str | None = None
    frameworks: list[FrameworkInfo] = Field(default_factory=list)
    build_tools: list[str] = Field(default_factory=list)
    package_managers: list[str] = Field(default_factory=list)
    runtime_versions: dict[str, str] = Field(
        default_factory=dict,
        description="Runtime name → version (e.g. node: '20.x', python: '3.11')",
    )


class DatabaseResult(AnalysisResult):
    """Dimension 2: ORM, migrations, schema conventions."""

    database_type: str | None = None  # postgres, mysql, sqlite, mongodb, etc.
    orm: str | None = None
    orm_version: str | None = None
    migration_tool: str | None = None
    migration_directory: str | None = None
    schema_naming_convention: str | None = None  # snake_case, camelCase, PascalCase
    relationship_patterns: list[str] = Field(default_factory=list)
    has_seeds: bool = False
    seed_directory: str | None = None
    connection_pooling: str | None = None
    schema_patterns: list[str] = Field(default_factory=list)


class AuthResult(AnalysisResult):
    """Dimension 3: Authentication & authorization patterns."""

    auth_strategy: str | None = None  # jwt, session, oauth, saml, etc.
    auth_middleware: list[str] = Field(default_factory=list)
    permission_model: str | None = None  # rbac, abac, acl, etc.
    protected_route_patterns: list[str] = Field(default_factory=list)
    auth_directories: list[str] = Field(default_factory=list)
    mfa_methods: list[str] = Field(default_factory=list)
    oauth_providers: list[str] = Field(default_factory=list)
    rate_limiting: str | None = None


# ---------------------------------------------------------------------------
# HIGH IMPACT — Breaks production functionality
# ---------------------------------------------------------------------------


class DependencyInfo(BaseModel):
    name: str = Field(min_length=1)
    version: str | None = None
    is_dev: bool = False
    category: str = ""  # e.g. "http-client", "ui-framework", "testing"


class DependenciesResult(AnalysisResult):
    """Dimension 4: Core and dev dependencies, key libraries."""

    dependencies: list[DependencyInfo] = Field(default_factory=list)
    dependency_manifest_files: list[str] = Field(default_factory=list)
    lock_file: str | None = None


class ErrorHandlingResult(AnalysisResult):
    """Dimension 5: Error handling & logging patterns."""

    error_strategy: str | None = None  # exceptions, result-types, error-codes
    logging_framework: str | None = None
    logging_config_file: str | None = None
    monitoring_integration: str | None = None  # sentry, datadog, etc.
    error_response_format: str | None = None  # json, html, etc.
    custom_error_classes: list[str] = Field(default_factory=list)
    structured_logging: bool = False
    error_recovery_patterns: list[str] = Field(default_factory=list)


class I18nResult(AnalysisResult):
    """Dimension 6: Internationalization / localization."""

    i18n_framework: str | None = None
    translation_file_format: str | None = None  # json, yaml, po, xliff
    translation_directories: list[str] = Field(default_factory=list)
    default_locale: str | None = None
    supported_locales: list[str] = Field(default_factory=list)
    string_externalization_pattern: str | None = None
    message_format: str | None = None  # icu, simple-key-value
    rtl_languages: list[str] = Field(default_factory=list)
    translation_management: str | None = None  # crowdin, lokalise, phrase, etc.


class StateManagementResult(AnalysisResult):
    """Dimension 7: State management patterns."""

    state_library: str | None = None  # redux, zustand, mobx, vuex, pinia, ngrx
    data_fetching_library: str | None = None  # react-query, swr, apollo
    store_structure: str | None = None
    state_patterns: list[str] = Field(default_factory=list)
    form_library: str | None = None
    realtime_library: str | None = None


class EnvConfigResult(AnalysisResult):
    """Dimension 8: Environment & configuration."""

    config_approach: str | None = None  # dotenv, yaml, vault, etc.
    env_files: list[str] = Field(default_factory=list)
    has_docker: bool = False
    dockerfile_path: str | None = None
    docker_compose_path: str | None = None
    feature_flags_system: str | None = None
    config_directories: list[str] = Field(default_factory=list)
    secrets_management: str | None = None
    kubernetes_detected: bool = False


class GitWorkflowResult(AnalysisResult):
    """Dimension 9: Git workflow & conventions."""

    git_platform: str | None = None  # github, gitlab, azure-devops, bitbucket
    branch_naming_strategy: str | None = None
    commit_message_format: str | None = None  # conventional, angular, freeform
    pr_template_path: str | None = None
    merge_strategy: str | None = None  # squash, rebase, merge
    required_reviewers: int | None = None
    ci_config_path: str | None = None
    release_tagging: str | None = None
    codeowners_path: str | None = None
    changelog_path: str | None = None
    release_tool: str | None = None


# ---------------------------------------------------------------------------
# MEDIUM IMPACT — Quality and compliance
# ---------------------------------------------------------------------------


class DirectoryPattern(BaseModel):
    path: str
    purpose: str = ""


class StructureResult(AnalysisResult):
    """Dimension 10: Project structure patterns."""

    root_directories: list[str] = Field(default_factory=list)
    source_directories: list[str] = Field(default_factory=list)
    key_directories: list[DirectoryPattern] = Field(default_factory=list)
    module_organization: str | None = None  # flat, feature-based, layered, domain-driven
    is_monorepo: bool = False
    monorepo_tool: str | None = None  # lerna, nx, turborepo, pnpm-workspaces
    sub_projects: list[str] = Field(default_factory=list)


class ConventionsResult(AnalysisResult):
    """Dimension 11: Naming, formatting, import conventions."""

    linter: str | None = None
    linter_config_path: str | None = None
    formatter: str | None = None
    formatter_config_path: str | None = None
    editorconfig_path: str | None = None
    import_ordering: str | None = None
    naming_convention: str | None = None  # camelCase, snake_case, PascalCase
    file_naming_convention: str | None = None  # kebab-case, PascalCase, camelCase


class SecurityResult(AnalysisResult):
    """Dimension 12: Security patterns."""

    input_validation: str | None = None  # zod, joi, class-validator, etc.
    cors_config: str | None = None
    secrets_management: str | None = None
    csp_headers: bool = False
    security_middleware: list[str] = Field(default_factory=list)
    vulnerability_scanning: str | None = None


class TestingResult(AnalysisResult):
    """Dimension 13: Testing patterns."""

    test_framework: str | None = None
    test_runner: str | None = None
    test_directories: list[str] = Field(default_factory=list)
    test_file_pattern: str | None = None  # *.test.ts, *_test.py, *Test.java
    mocking_library: str | None = None
    coverage_tool: str | None = None
    coverage_config_path: str | None = None
    fixture_patterns: list[str] = Field(default_factory=list)
    e2e_framework: str | None = None
    api_testing_tools: list[str] = Field(default_factory=list)
    visual_regression_tool: str | None = None
    contract_testing_tool: str | None = None
    test_organization: str | None = None  # collocated, separated, bdd
    snapshot_testing: bool = False


class CICDResult(AnalysisResult):
    """Dimension 14: CI/CD pipeline detection."""

    platform: str | None = None  # github-actions, gitlab-ci, azure-pipelines, jenkins
    config_path: str | None = None
    build_steps: list[str] = Field(default_factory=list)
    deployment_targets: list[str] = Field(default_factory=list)
    required_checks: list[str] = Field(
        default_factory=list,
        description=(
            "Reserved: branch-protection required checks are not detectable offline; "
            "kept empty unless populated by a future integration."
        ),
    )
    caching_detected: bool = False
    matrix_builds: bool = False
    deployment_patterns: list[str] = Field(default_factory=list)
    release_tool: str | None = None


class DesignUIResult(AnalysisResult):
    """Dimension 15: Design/UI patterns."""

    css_methodology: str | None = None  # modules, css-in-js, tailwind, scss, bem
    component_library: str | None = None  # material-ui, ant-design, chakra, cds
    component_library_version: str | None = None
    design_tokens_format: str | None = None
    design_tokens_path: str | None = None
    responsive_strategy: str | None = None
    theme_provider: str | None = None
    styling_directories: list[str] = Field(default_factory=list)
    uses_shared_design_system: bool = False
    shared_design_system_name: str | None = None
    icon_library: str | None = None
    component_doc_tool: str | None = None
    font_strategy: str | None = None


class AccessibilityResult(AnalysisResult):
    """Dimension 16: Accessibility compliance."""

    wcag_level: str | None = None  # A, AA, AAA
    a11y_testing_tools: list[str] = Field(default_factory=list)
    aria_usage_detected: bool = False
    semantic_html_score: str | None = None  # low, medium, high
    keyboard_navigation: bool = False
    color_contrast_config: str | None = None
    form_accessibility: list[str] = Field(default_factory=list)
    focus_management_patterns: list[str] = Field(default_factory=list)


class APIResult(AnalysisResult):
    """Dimension 17: API patterns."""

    api_style: str | None = None  # rest, graphql, grpc, soap
    route_structure: str | None = None
    api_directories: list[str] = Field(default_factory=list)
    openapi_spec_path: str | None = None
    request_validation: str | None = None
    response_format: str | None = None  # json, xml
    pagination_pattern: str | None = None
    versioning_strategy: str | None = None  # url-path, header, query-param


class PerformanceResult(AnalysisResult):
    """Dimension 18: Performance patterns."""

    caching_strategy: str | None = None  # redis, in-memory, cdn
    lazy_loading: bool = False
    code_splitting: bool = False
    bundle_size_config: str | None = None
    image_optimization: str | None = None
    n_plus_one_prevention: str | None = None
    performance_monitoring: str | None = None
    web_vitals_monitoring: str | None = None
    service_worker_detected: bool = False
    cdn_detected: str | None = None


class FrontendPatternsResult(AnalysisResult):
    """Dimension: Frontend UI patterns (layout, forms, modals, lists, error, loading)."""

    layout_patterns: list[str] = Field(default_factory=list)
    form_libraries: list[str] = Field(default_factory=list)
    modal_pattern: str | None = None
    list_virtualization: str | None = None
    error_boundary: bool = False
    loading_patterns: list[str] = Field(default_factory=list)
    routing_library: str | None = None
    animation_library: str | None = None


class UserFlowsResult(AnalysisResult):
    """Dimension: User flows (route structure, navigation graph, task flows)."""

    route_count: int = 0
    route_files: list[str] = Field(default_factory=list)
    navigation_type: str | None = None
    auth_protected_routes: bool = False
    has_404_page: bool = False
    has_error_page: bool = False
    page_directories: list[str] = Field(default_factory=list)
    dynamic_routes: list[str] = Field(default_factory=list)
    lazy_routes: bool = False


# ---------------------------------------------------------------------------
# DEEP — Cursor-assisted only (populated during Phase 2)
# ---------------------------------------------------------------------------


class BoundedContextEntry(BaseModel):
    """A bounded context with evidence of where it exists."""

    name: str
    evidence: str | None = None


class ModuleBoundaryEntry(BaseModel):
    """Module dependency info with evidence."""

    depends_on: list[str] = Field(default_factory=list)
    evidence: str | None = None


class DomainVocabularyEntry(BaseModel):
    """A domain term with evidence of usage."""

    term: str
    evidence: str | None = None


class EntityRelationshipEntry(BaseModel):
    """An entity relationship with evidence."""

    model_config = ConfigDict(populate_by_name=True)

    from_entity: str = Field(alias="from")
    to_entity: str = Field(alias="to")
    type: str = ""
    evidence: str | None = None


class BusinessLogicLocationEntry(BaseModel):
    """A location where business logic lives."""

    path: str
    description: str = ""
    evidence: str | None = None


class CodeOrganizationHabitEntry(BaseModel):
    """A code organization pattern with evidence."""

    pattern: str
    evidence: str | None = None


class ArchitectureDeepResult(BaseModel):
    """Deep analysis: architecture & module boundaries (populated by Cursor)."""

    layering_pattern: str | None = None
    layering_evidence: str | None = None
    dependency_direction: str | None = None
    dependency_evidence: str | None = None
    bounded_contexts: list[BoundedContextEntry] = Field(default_factory=list)
    module_boundaries: dict[str, ModuleBoundaryEntry] = Field(default_factory=dict)


class DomainModelDeepResult(BaseModel):
    """Deep analysis: domain model & business logic (populated by Cursor)."""

    domain_vocabulary: list[DomainVocabularyEntry] = Field(default_factory=list)
    entity_relationships: list[EntityRelationshipEntry] = Field(default_factory=list)
    business_logic_locations: list[BusinessLogicLocationEntry] = Field(
        default_factory=list
    )


class ImplicitConventionsDeepResult(BaseModel):
    """Deep analysis: implicit conventions (populated by Cursor)."""

    naming_philosophy: str | None = None
    naming_evidence: str | None = None
    abstraction_level: str | None = None
    abstraction_evidence: str | None = None
    code_organization_habits: list[CodeOrganizationHabitEntry] = Field(
        default_factory=list
    )
    error_handling_philosophy: str | None = None
    error_evidence: str | None = None
