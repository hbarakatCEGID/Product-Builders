"""Cursor-native enrichment meta-rule generator.

Generates 4 batched enrichment meta-rules that instruct Cursor to rewrite
template-generated .mdc rules with project-specific depth. Cursor reads the
template rules + actual codebase, then produces enriched versions.

Batches are grouped by impact tier to prevent context window decay:
  1. Critical  — database, auth-patterns, security
  2. Architecture — architecture, coding-conventions, error-handling, api-patterns
  3. Frontend — design-system, frontend-patterns, user-flows, state-and-config
  4. Supporting — testing, performance, accessibility, i18n, cicd, git-workflow
"""

from __future__ import annotations

import logging
from pathlib import Path

from product_builders.deep_analysis.prompts import build_gap_aware_questions
from product_builders.generators.base import BaseGenerator
from product_builders.generators.registry import register
from product_builders.models.profile import ProductProfile
from product_builders.models.scopes import ContributorRole

logger = logging.getLogger(__name__)

# Batch name → list of rule filenames in that batch
ENRICHMENT_BATCHES: dict[str, list[str]] = {
    "critical": ["database.mdc", "auth-patterns.mdc", "security.mdc"],
    "architecture": ["architecture.mdc", "coding-conventions.mdc", "error-handling.mdc", "api-patterns.mdc"],
    "frontend": ["design-system.mdc", "frontend-patterns.mdc", "user-flows.mdc", "state-and-config.mdc"],
    "supporting": ["testing.mdc", "performance.mdc", "accessibility.mdc", "i18n.mdc", "cicd.mdc", "git-workflow.mdc"],
}

# Per-rule analysis instructions: what files to look at, what sections to produce
RULE_INSTRUCTIONS: dict[str, dict[str, list[str]]] = {
    "database.mdc": {
        "analyze_hints": [
            "Database client/ORM files (check `src/lib/`, `src/db/`, `prisma/`, `supabase/`)",
            "Migration files and directories",
            "Query patterns in API route handlers",
            "Schema definitions or model files",
        ],
        "required_sections": [
            "Database type and access pattern (how THIS project queries the DB)",
            "Migration workflow (exact commands, directory, tooling)",
            "Query patterns with DO/DON'T code examples from the codebase",
            "Entity relationships (tables, models, their connections)",
            "Schema conventions (naming, types, constraints)",
        ],
    },
    "auth-patterns.mdc": {
        "analyze_hints": [
            "Auth client/middleware files (check `src/lib/auth/`, `src/middleware*`, `src/lib/supabase/`)",
            "Protected API routes — how they validate authentication",
            "Role/permission checks in route handlers or middleware",
            "Session/token handling patterns",
        ],
        "required_sections": [
            "Auth strategy details (how auth works in THIS project, not generic)",
            "Auth middleware/guard pattern with DO/DON'T code examples",
            "Protected vs public routes (which routes need auth, which don't)",
            "Permission model (how roles/permissions are checked)",
            "Auth-related file locations",
        ],
    },
    "security.mdc": {
        "analyze_hints": [
            "Input validation patterns (check API route handlers for validation)",
            "Environment files and secrets handling",
            "CORS configuration",
            "Security middleware or headers",
        ],
        "required_sections": [
            "Input validation pattern with DO/DON'T code examples",
            "Secrets management (how env vars and secrets are handled)",
            "Security middleware stack",
            "CORS and headers configuration",
        ],
    },
    "architecture.mdc": {
        "analyze_hints": [
            "Top-level directory structure and module organization",
            "Import patterns across modules (dependency direction)",
            "Shared utility/helper locations",
            "Feature vs layer organization",
        ],
        "required_sections": [
            "Architecture pattern (layered, feature-based, etc.) with evidence",
            "Module boundaries table (module → depends on → evidence)",
            "Dependency direction rule with DO/DON'T examples",
            "Where to place new code (decision tree by type of change)",
        ],
    },
    "coding-conventions.mdc": {
        "analyze_hints": [
            "5+ representative source files for naming patterns",
            "Import ordering across files",
            "Linter/formatter config files",
            "Type annotation patterns",
        ],
        "required_sections": [
            "Naming conventions with real examples from the codebase",
            "Import ordering pattern with example",
            "Code organization habits (how features are structured)",
            "DO/DON'T pairs showing the project's actual style vs common mistakes",
        ],
    },
    "error-handling.mdc": {
        "analyze_hints": [
            "Error handling in API route handlers",
            "Custom error classes or error utilities",
            "Logging patterns across the codebase",
            "Error response format in API responses",
        ],
        "required_sections": [
            "Error handling strategy with code examples from the project",
            "Custom error classes (if any) with usage patterns",
            "Logging pattern with DO/DON'T examples",
            "API error response format with example",
        ],
    },
    "api-patterns.mdc": {
        "analyze_hints": [
            "API route handler files (check route.ts, controller files)",
            "Request validation patterns",
            "Response format consistency",
            "Pagination, filtering, sorting patterns",
        ],
        "required_sections": [
            "Route handler pattern with DO/DON'T code examples",
            "Request validation approach with examples",
            "Response format (standard envelope, error format)",
            "Complete route inventory with HTTP methods",
        ],
    },
    "design-system.mdc": {
        "analyze_hints": [
            "Component library usage patterns (imports, composition)",
            "Styling approach (Tailwind classes, CSS modules, etc.)",
            "Shared component directory",
            "Theme/token configuration",
        ],
        "required_sections": [
            "Component library usage with DO/DON'T examples",
            "Styling pattern with examples from the project",
            "Shared components inventory",
            "Theme/design token usage",
        ],
    },
    "frontend-patterns.mdc": {
        "analyze_hints": [
            "Form implementations across the app",
            "Modal/dialog components",
            "Loading state patterns (skeletons, spinners)",
            "Error boundary components",
        ],
        "required_sections": [
            "Form handling pattern with code examples",
            "Loading state pattern with examples",
            "Modal/dialog pattern with examples",
            "Component composition patterns",
        ],
    },
    "user-flows.mdc": {
        "analyze_hints": [
            "Page components and their route structure",
            "Navigation components and patterns",
            "Protected vs public pages",
            "Dynamic route parameters",
        ],
        "required_sections": [
            "Complete route map organized by feature area",
            "Route naming convention with examples",
            "Navigation pattern",
            "Protected routes and auth requirements",
        ],
    },
    "state-and-config.mdc": {
        "analyze_hints": [
            "State management usage (Context, Redux, Zustand, etc.)",
            "Data fetching patterns (hooks, API calls)",
            "Environment configuration files",
            "Feature flag patterns",
        ],
        "required_sections": [
            "State management pattern with code examples",
            "Data fetching pattern with DO/DON'T examples",
            "Environment configuration approach",
        ],
    },
    "testing.mdc": {
        "analyze_hints": [
            "Existing test files for patterns",
            "Test setup/configuration files",
            "Mock and fixture patterns",
            "Test directory structure",
        ],
        "required_sections": [
            "Test file pattern with example from the project",
            "Test structure (describe/it, arrange-act-assert, etc.)",
            "Mocking pattern with examples",
            "How to run tests",
        ],
    },
    "performance.mdc": {
        "analyze_hints": [
            "Image optimization usage",
            "Code splitting / lazy loading patterns",
            "Caching configuration",
            "Bundle configuration",
        ],
        "required_sections": [
            "Performance patterns used in this project",
            "Image and asset optimization approach",
            "Caching strategy",
        ],
    },
    "accessibility.mdc": {
        "analyze_hints": [
            "ARIA attribute usage in components",
            "Semantic HTML patterns",
            "Keyboard navigation implementations",
            "Form accessibility patterns",
        ],
        "required_sections": [
            "Accessibility patterns found in the project",
            "ARIA usage examples",
            "Semantic HTML patterns",
        ],
    },
    "i18n.mdc": {
        "analyze_hints": [
            "Translation files and directories",
            "i18n library usage in components",
            "Locale configuration",
        ],
        "required_sections": [
            "i18n setup and usage pattern",
            "How to add new translations",
        ],
    },
    "cicd.mdc": {
        "analyze_hints": [
            "CI/CD configuration files",
            "Build scripts and commands",
            "Deployment configuration",
        ],
        "required_sections": [
            "CI/CD pipeline overview",
            "Build and deployment commands",
            "Required checks before merge",
        ],
    },
    "git-workflow.mdc": {
        "analyze_hints": [
            "PR templates and contributing guidelines",
            "Branch naming in recent commits",
            "Commit message patterns",
            "CODEOWNERS file",
        ],
        "required_sections": [
            "Commit message convention with examples from git log",
            "Branch naming pattern",
            "PR workflow and review requirements",
        ],
    },
}


def _build_phase_context(rule_names: list[str]) -> list[dict[str, str | list[str]]]:
    """Build per-rule instruction context for a phase."""
    rules = []
    for rule_name in rule_names:
        instructions = RULE_INSTRUCTIONS.get(rule_name, {})
        rules.append({
            "name": rule_name,
            "analyze_hints": instructions.get("analyze_hints", []),
            "required_sections": instructions.get("required_sections", []),
        })
    return rules


class EnrichmentGenerator(BaseGenerator):
    """Generates a single self-pacing enrichment meta-rule for Cursor-native rule enrichment."""

    @property
    def name(self) -> str:
        return "Enrichment Meta-Rule Generator"

    def generate(
        self,
        profile: ProductProfile,
        output_dir: Path,
        *,
        role: ContributorRole | None = None,
    ) -> list[Path]:
        rules_dir = output_dir / ".cursor" / "rules"
        gap_questions = build_gap_aware_questions(profile)

        # Build phase contexts from batch definitions
        phases = {
            batch_name: _build_phase_context(rule_names)
            for batch_name, rule_names in ENRICHMENT_BATCHES.items()
        }

        content = self.render_template(
            "enrich-all.mdc.j2",
            profile=profile,
            gap_questions=gap_questions,
            phases=phases,
        )
        path = self.write_file(rules_dir / "enrich-all.mdc", content)
        return [path]


register(EnrichmentGenerator())
