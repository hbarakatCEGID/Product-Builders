# Analyzer Deep Research & Improvement Plan

## Overview

Deep analysis of all 20 offline heuristic analyzers. For each: what it does today, what it misses, how to improve it, and what to add. Includes a cross-reference of which fields are actually consumed by templates vs. wasted.

---

## CRITICAL IMPACT (3 analyzers)

### 1. Tech Stack (`tech_stack.py`)

**What it does:** Counts file extensions for language percentages, matches 23 frameworks from dependency names, detects 10 build tools from config files, 13 package managers from lock files, runtime versions from .nvmrc/.python-version/pom.xml.

**What it misses:**
- Modern frameworks: Astro, Hono, Elysia, SvelteKit, SolidJS, T3 Stack
- Python async: Quart, Sanic, Litestar
- Elixir: Phoenix, Ecto. Scala: Play Framework
- Version normalization (stores raw `"^18.0.0"` instead of `18.0.0`)
- Language weighting (counts test/config files equally with source code)
- Template languages: Jinja2, Handlebars, ERB not detected
- Deno/Bun as runtimes (only as package managers)
- No TypeScript vs JavaScript ratio tracking

**Template usage:** ALL fields consumed. Fully utilized dimension.

**Improvements:**
| Change | Impact | Effort |
|--------|--------|--------|
| Add 10+ missing frameworks (Astro, Hono, Litestar, Phoenix, etc.) | HIGH | LOW |
| Normalize version strings to semver | MEDIUM | LOW |
| Weight source files (exclude tests/config from language %) | HIGH | MEDIUM |
| Add `typescript_usage: float` field (TS vs JS ratio) | MEDIUM | LOW |
| Add Ruby (.ruby-version), Rust (rust-toolchain.toml) version detection | LOW | LOW |
| Detect metaframeworks (T3, MERN, PERN) | LOW | MEDIUM |

---

### 2. Database (`database.py`)

**What it does:** Detects 13 ORMs via dependency names, 8 database types via 50+ indicators, migration tool/directory per ORM, schema naming convention from Prisma/hardcoded per framework, seeds from directory patterns, relationship patterns via regex.

**What it misses:**
- `orm_version` is always None (never extracted from package.json)
- Only returns ONE database type (most apps use multiple: PostgreSQL + Redis)
- No connection pooling detection (pgBouncer, HikariCP)
- Missing databases: CockroachDB, YugabyteDB, Spanner, Vitess
- No UUID vs auto-increment PK detection
- No soft delete pattern detection (deleted_at fields)
- No audit field detection (created_at, updated_at)
- TypeORM @OneToMany/@ManyToMany decorators not scanned
- Sequelize associations not scanned

**Template usage:** Most fields used. `relationship_patterns` and `orm_version` are NEVER referenced in templates (wasted).

**Improvements:**
| Change | Impact | Effort |
|--------|--------|--------|
| Extract ORM version from package.json/lock files | HIGH | LOW |
| Return array of ALL detected databases (not just first) | HIGH | MEDIUM |
| Add TypeORM/Sequelize/Drizzle relationship scanning | MEDIUM | MEDIUM |
| Add connection pooling detection | MEDIUM | LOW |
| Add UUID vs integer PK detection (AST: scan model definitions) | MEDIUM | MEDIUM |
| Add soft delete / audit field detection | LOW | MEDIUM |
| Remove unused `relationship_patterns` field or wire into templates | LOW | LOW |

---

### 3. Auth (`auth.py`)

**What it does:** Detects 9 auth strategies from dependency indicators, permission models (RBAC/ABAC/ACL) from keyword matching, protected route patterns via regex on 20 files, auth directories, auth middleware. AST enhancement adds decorator-based detection and import tracing.

**What it misses:**
- Returns only ONE strategy (most apps use JWT + Session or OAuth + API Key)
- No MFA/2FA detection
- No passwordless auth (FIDO2, WebAuthn, magic links)
- No OAuth provider detection (which providers: Google, GitHub, Microsoft?)
- No token refresh pattern detection
- No cookie security flags (Secure, HttpOnly, SameSite)
- No rate limiting / brute force protection detection
- No CSRF protection detection
- No route protection coverage estimate (% of routes protected)
- Permission model detection is fragile (keyword "role" in any file = RBAC)

**Template usage:** `token_handling` and `session_management` are NEVER referenced (wasted).

**Improvements:**
| Change | Impact | Effort |
|--------|--------|--------|
| Return array of auth strategies (not just one) | HIGH | MEDIUM |
| Add OAuth provider detection (scan for google, github configs) | HIGH | MEDIUM |
| Add MFA/2FA detection (scan for totp, authenticator, webauthn deps) | MEDIUM | LOW |
| Add cookie security flags detection | MEDIUM | MEDIUM |
| Add rate limiting detection (express-rate-limit, etc.) | MEDIUM | LOW |
| Estimate route protection coverage (protected / total routes) | MEDIUM | HIGH |
| Remove or wire unused `token_handling`, `session_management` fields | LOW | LOW |

---

## HIGH IMPACT (6 analyzers)

### 4. Dependencies (`dependencies.py`)

**What it does:** Parses package.json, requirements.txt, pom.xml, .csproj for dependency names/versions. Categorizes 45+ known libraries. Detects lock files.

**What it misses:**
- pyproject.toml dependencies NOT actually parsed (registered but skipped)
- No Gemfile, Cargo.toml, go.mod parsing
- No monorepo workspace dependencies
- No transitive dependency analysis (only reads manifests)
- Version strings not normalized
- No unused dependency detection

**Template usage:** ENTIRE DIMENSION IS UNUSED. No template references DependenciesResult. This is dead data.

**Improvements:**
| Change | Impact | Effort |
|--------|--------|--------|
| Create `dependencies.mdc.j2` template to actually USE this data | HIGH | MEDIUM |
| Parse pyproject.toml `[project]` dependencies properly | HIGH | MEDIUM |
| Add Gemfile, Cargo.toml, go.mod parsing | MEDIUM | MEDIUM |
| Parse lock files for exact versions | MEDIUM | HIGH |
| Add unused dependency detection (via AST import cross-reference) | LOW | HIGH |

---

### 5. Error Handling (`error_handling.py`)

**What it does:** Detects 13 logging frameworks, 7 monitoring services, error strategy (exceptions vs result-types by counting throw/raise), error response format via regex, custom error classes. AST enhancement adds precise class detection.

**What it misses:**
- Returns only ONE logging framework (apps often use multiple)
- `throw`/`raise` counting includes comments and strings (false positives)
- No structured logging detection (JSON logs, OpenTelemetry)
- No error recovery patterns (retry, circuit breaker, fallback)
- No error hierarchy detection (which error extends which)
- No error boundary / global handler detection
- No log level configuration detection

**Template usage:** `logging_config_file` barely referenced. All other fields used.

**Improvements:**
| Change | Impact | Effort |
|--------|--------|--------|
| Return array of logging frameworks | MEDIUM | LOW |
| AST-based throw/raise counting (skip comments/strings) | HIGH | MEDIUM |
| Add structured logging detection (JSON, OpenTelemetry) | MEDIUM | LOW |
| Add error recovery pattern detection (retry, circuit breaker) | MEDIUM | MEDIUM |
| Add error hierarchy from AST (class X extends Y) | LOW | MEDIUM |

---

### 6. i18n (`i18n.py`)

**What it does:** Detects 11 frameworks via dependencies, translation file formats (JSON/YAML/PO/XLIFF), translation directories, locales from directory names, default locale, string externalization patterns.

**What it misses:**
- No message format detection (simple key-value vs ICU MessageFormat)
- No translation completeness metrics (% of keys per locale)
- No RTL language detection
- No date/time/number/currency formatting detection
- No Crowdin/Lokalise/Weblate integration detection
- No namespace/module detection for i18next
- Locale regex too simple (misses zh-Hans-CN)

**Template usage:** All fields used. `string_externalization_pattern` provides minimal value.

**Improvements:**
| Change | Impact | Effort |
|--------|--------|--------|
| Detect message format type (ICU vs simple) | MEDIUM | MEDIUM |
| Add RTL language detection from locale list | MEDIUM | LOW |
| Add translation tool detection (Crowdin, Lokalise configs) | LOW | LOW |
| Parse i18next config for namespaces | LOW | MEDIUM |
| Add translation completeness estimate | LOW | HIGH |

---

### 7. State Management (`state_management.py`)

**What it does:** Detects 13 state libraries, 10 data fetching libraries, store structure (modular vs flat), state patterns (slices, sagas, etc.). AST enhancement verifies actual imports.

**What it misses:**
- Returns only ONE state lib + ONE data fetching lib (hybrid setups common)
- No form state detection (react-hook-form, formik) — separate from global state
- No side effects handler detection (saga, thunk, epic)
- No state persistence detection (localStorage, sessionStorage)
- No real-time updates detection (WebSocket, SSE)
- Missing: tRPC, Relay, Easy-Peasy, signal-based state (SolidJS, Qwik)

**Template usage:** All fields used in state-and-config.mdc.

**Improvements:**
| Change | Impact | Effort |
|--------|--------|--------|
| Return arrays for state_library and data_fetching_library | HIGH | LOW |
| Add form library detection (separate field) | MEDIUM | LOW |
| Add side effects handler detection (saga/thunk/epic) | MEDIUM | LOW |
| Add state persistence detection | LOW | LOW |
| Add tRPC, Relay detection | LOW | LOW |

---

### 8. Environment & Config (`env_config.py`)

**What it does:** Detects 5 config approaches, 7 .env files, Docker/Compose, 6 feature flag services, config directories.

**What it misses:**
- Returns only ONE config approach (apps use multiple)
- No secrets management (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager)
- No Kubernetes/container orchestration detection
- No config schema validation detection (Zod/Joi for config)
- Docker analysis is presence-only (no content parsing)
- Missing feature flag services: Split.io, Statsig, Firebase Remote Config

**Template usage:** All fields used in state-and-config.mdc.

**Improvements:**
| Change | Impact | Effort |
|--------|--------|--------|
| Return array of config approaches | MEDIUM | LOW |
| Add secrets management detection | MEDIUM | LOW |
| Add Kubernetes detection (k8s manifests, Helm charts) | MEDIUM | LOW |
| Add config validation detection (Zod/Joi for config) | LOW | LOW |
| Parse Dockerfile for base image and multi-stage detection | LOW | MEDIUM |

---

### 9. Git Workflow (`git_workflow.py`)

**What it does:** Detects 4 git platforms, 9 CI systems, PR templates, commit format (conventional via commitlint), branch strategy from workflow files.

**What it misses:**
- No CODEOWNERS detection
- No release strategy detection (semantic-release, changesets)
- No branch protection rules (offline limitation, but CODEOWNERS is detectable)
- No changelog detection (CHANGELOG.md)
- No commit signing detection
- No squash/rebase/merge strategy detection from workflow files
- Commit format only detects conventional commits (misses gitmoji, JIRA prefixes)

**Template usage:** `ci_config_path` and `release_tagging` are NEVER referenced (wasted).

**Improvements:**
| Change | Impact | Effort |
|--------|--------|--------|
| Add CODEOWNERS detection | HIGH | LOW |
| Add changelog detection (CHANGELOG.md, HISTORY.md) | MEDIUM | LOW |
| Add semantic-release / changesets detection | MEDIUM | LOW |
| Detect gitmoji, JIRA-prefix commit formats | LOW | LOW |
| Remove or wire unused `ci_config_path`, `release_tagging` | LOW | LOW |

---

## MEDIUM IMPACT (11 analyzers)

### 10. Structure (`structure.py`)

**Detects:** Root/source/key directories (80+ known patterns), organization pattern (feature/layered/domain/flat), monorepo tools, sub-projects.

**Misses:** Shallow depth (1 level), no nested pattern detection, no workspace boundary detection, polyrepo/submodule detection.

**Template usage:** `root_directories` and `sub_projects` NEVER referenced.

**Top improvements:** Parse package.json `workspaces` field, detect workspace boundaries, add nesting depth info.

---

### 11. Conventions (`conventions.py`)

**Detects:** 10+ ESLint configs, 8+ formatters, .editorconfig, naming convention from AST/file sampling, file naming convention.

**Misses:** No linter rule parsing (just file existence), no import ordering detection (isort), no comment style detection (JSDoc/docstring), no max line length detection.

**Template usage:** All fields used. `import_ordering` provides minimal value.

**Top improvements:** Parse actual linter config rules, add import ordering detection, add comment convention detection.

---

### 12. Security (`security.py`)

**Detects:** Input validation libs, CORS config, secrets management (vault, sops), CSP via helmet, security middleware, vulnerability scanners (snyk, bandit, dependabot).

**Misses:** No HTTPS enforcement detection, no rate limiting, no SQL injection prevention verification, no authentication method detection (overlaps with auth analyzer), no actual config parsing.

**Template usage:** All fields used. `vulnerability_scanning` barely referenced.

**Top improvements:** Parse security configs, add rate limiting detection, add HTTPS enforcement.

---

### 13. Testing (`testing.py`)

**Detects:** 14+ frameworks, test dirs, file patterns (sampling 200 files), 10+ mocking libs, 8 coverage tools, 8 E2E frameworks, fixtures.

**Misses:** No test organization detection (unit/integration/e2e separation), no coverage threshold detection, no snapshot testing detection, no parallel execution config, no test runner vs framework distinction.

**Template usage:** `coverage_config_path` barely referenced. All others used.

**Top improvements:** Detect test organization strategy, extract coverage thresholds from config, add snapshot testing detection.

---

### 14. CI/CD (`cicd.py`)

**Detects:** 9 platforms, build steps from GitHub Actions (first line only), 11 deployment targets.

**Misses:** Shallow step extraction (first line of run commands), no build matrix detection, no caching detection, no secrets management, no artifact retention, truncates at 20 steps.

**Template usage:** ENTIRE DIMENSION UNUSED. No template references CICDResult. Dead data.

**Top improvements:** Create `cicd.mdc.j2` template, parse full workflow files, detect build matrix and caching.

---

### 15. Design/UI (`design.py`)

**Detects:** 18+ component libraries, 9 CSS methodologies, design tokens (JSON/YAML/SCSS/CSS vars), responsive strategy, theme providers, shared design system.

**Misses:** No Figma integration, no icon library detection, no typography/font detection, no Tailwind config parsing, no Storybook/component doc tool detection, no color palette extraction.

**Template usage:** `theme_provider` NEVER referenced.

**Top improvements:** Add icon library detection, Storybook detection, parse Tailwind config for customizations.

---

### 16. Accessibility (`accessibility.py`)

**Detects:** WCAG level from config, 9 a11y tools, ARIA usage (binary), semantic HTML score, keyboard navigation, color contrast config.

**Misses:** No actual WCAG compliance scanning, no form accessibility detection, no alt text coverage, no focus management detection, no skip link detection.

**Template usage:** `semantic_html_score`, `keyboard_navigation`, `color_contrast_config` are ALL NEVER referenced. 3 wasted fields.

**Top improvements:** Wire unused fields into template, add form accessibility detection, add alt text coverage.

---

### 17. API (`api.py`)

**Detects:** API style (REST/GraphQL/gRPC), route structure, API dirs, OpenAPI spec, validation libs, response format, pagination (cursor/offset), versioning (URL path). AST enhancement adds decorator/import detection.

**Misses:** Pagination detection is fragile (keyword matching), versioning misses header/Accept strategies, no GraphQL subscription detection, no webhook detection, no error response format detection.

**Template usage:** `openapi_spec_path` referenced but not validated. All others used.

**Top improvements:** Parse OpenAPI specs, add versioning strategy variants, add webhook detection.

---

### 18. Performance (`performance.py`)

**Detects:** Caching (Redis, in-memory), lazy loading, code splitting, bundle config tools, image optimization, N+1 prevention, monitoring.

**Misses:** No web vitals monitoring, no compression detection (gzip/brotli), no CDN detection, no service worker/PWA, no font optimization, no performance budgets.

**Template usage:** `bundle_size_config` NEVER referenced.

**Top improvements:** Add web vitals detection, compression detection, CDN detection, service worker detection.

---

### 19. Frontend Patterns (`frontend_patterns.py`)

**Detects:** Layout patterns, 8+ form libraries, modal patterns, virtualization, error boundaries, loading patterns, routing, animation. AST enhancement adds component and import detection.

**Misses:** No component composition patterns (HOC, render props, compound), no async handling patterns, no responsive behavior detection, no state management patterns (overlaps with state_management).

**Template usage:** All fields used.

**Top improvements:** Add component composition pattern detection, responsive pattern detection.

---

### 20. User Flows (`user_flows.py`)

**Detects:** Page directories, routes (file-based), navigation type, auth-protected routes (pattern matching on 40 files), 404 page, error page.

**Misses:** No dynamic route detection ([id], :id parameters), no nested route detection, no lazy route loading, no middleware/guard detection per route, no redirect detection.

**Template usage:** All fields used.

**Top improvements:** Detect dynamic route parameters, nested routes, lazy-loaded routes.

---

## CROSS-CUTTING FINDINGS

### Dead Data (dimensions with no template)
| Dimension | Status | Action |
|-----------|--------|--------|
| `DependenciesResult` | NEVER used in any template | Create `dependencies.mdc.j2` OR remove analyzer |
| `CICDResult` | NEVER used in any template | Create `cicd.mdc.j2` OR remove analyzer |

### Wasted Fields (stored but never referenced)
| Dimension | Unused Fields |
|-----------|---------------|
| database | `relationship_patterns`, `orm_version` |
| auth | `token_handling`, `session_management` |
| git_workflow | `ci_config_path`, `release_tagging` |
| structure | `root_directories`, `sub_projects` |
| design_ui | `theme_provider` |
| accessibility | `semantic_html_score`, `keyboard_navigation`, `color_contrast_config` |
| performance | `bundle_size_config` |
| domain_model_deep | `domain_vocabulary` |

### `_should_generate()` Issues
| Template | Issue |
|----------|-------|
| `auth-patterns.mdc.j2` | Too loose — generates with just `auth_directories` (empty rule) |
| `accessibility.mdc.j2` | Too loose — generates with just `aria_usage_detected=true` |
| `api-patterns.mdc.j2` | Too loose — generates with just `business_logic_locations` |

---

## IMPLEMENTATION PLAN (Merged with Best Practices Research)

*Incorporates findings from 5 specialized research agents covering auth/security, database/state, testing/CI-CD, frontend/a11y, and devops/quality best practices.*

---

### Phase A: Quick Wins — Add Items to Detection Lists (2-3 days)

Data-only changes. No logic, no new fields, no new templates.

| Analyzer | What to Add | Count |
|----------|-------------|-------|
| **tech_stack** | 17 frameworks (Astro, Hono, Elysia, SvelteKit, SolidJS, Qwik, Litestar, FastHTML, Phoenix, H3, Nitro, TanStack Start, Analog, Quart, Sanic, SolidStart, Play) + 6 package managers (deno, pixi, conda, swift-pm, pub, cocoapods) + 2 build tools (deno, bun) | +25 |
| **database** | 13 ORMs (MikroORM, Objection, jOOQ, MyBatis, Ent, sqlx, sqlc, Dapper, Exposed, Peewee, SQLModel, GORM, Sequel) + 6 DB types (Cassandra, CockroachDB, Neon, PlanetScale, Turso, Supabase explicit) | +19 |
| **auth** | WebAuthn/passkeys, better-auth libs + Go (golang-jwt, goth, go-oidc) + Ruby (devise, omniauth, sorcery, rodauth) + .NET (ASP.NET Identity, Duende) + Java (spring-security, jjwt, keycloak) | +15 |
| **error_handling** | consola, OpenTelemetry, Grafana agent | +3 |
| **i18n** | svelte-i18n, typesafe-i18n, Lingui, Paraglide, rosetta, rust-i18n, go-i18n, ICU MessageFormat | +8 |
| **state_management** | NgRx Signals, Legend State, nanostores, TanStack Store + tRPC, Relay, ofetch, ky | +8 |
| **env_config** | 6 feature flag platforms: Statsig, Split.io, DevCycle, Flipt, OpenFeature, ConfigCat | +6 |
| **git_workflow** | CODEOWNERS, CHANGELOG.md, semantic-release, changesets, release-please, goreleaser, git-cliff, Mergify, gitmoji | +9 |
| **conventions** | 8 linter configs (oxlint, golangci-lint, clippy, detekt, ktlint, phpstan, phpcs, pmd) + 3 formatters (dprint, rustfmt, clang-format) | +11 |
| **security** | 5 validation libs (valibot, typebox, hibernate-validator, go-validator, dry-validation) + 7 rate limiters + 7 secrets mgmt (AWS/Azure/GCP/Doppler/Infisical/1Password/Sealed Secrets) + 6 vuln scanners (Trivy, gosec, Brakeman, bundler-audit, Socket, CodeQL) | +25 |
| **testing** | ava, Bun test + 7 mocking libs + 2 coverage tools + 2 E2E frameworks | +12 |
| **cicd** | 6 CI platforms (Drone, Woodpecker, Buildkite, TeamCity, Dagger, AppVeyor) + 9 deployment targets (Railway, SST, Pulumi, Terraform, CDK, SAM, Ansible, Helm, Kustomize) | +15 |
| **design** | 12 component libs (Ark UI, React Aria, Flowbite, HeroUI, Skeleton, Element Plus, Naive UI, Angular Material, PrimeNG, Kobalte, Corvu) + 8 CSS approaches (Vanilla Extract, Panda CSS, StyleX, UnoCSS, Linaria, PostCSS, Lightning CSS, goober) | +20 |
| **accessibility** | 10 a11y tools (axe-playwright, cypress-axe, storybook-a11y, vitest-axe, eslint-vuejs-a11y, angular-eslint-a11y, react-aria, radix-ui, ark-ui, focus-trap) | +10 |
| **performance** | 4 monitoring (Vercel Analytics, web-vitals, Lighthouse CI, Datadog RUM) + 2 caching + 1 image | +7 |
| **frontend_patterns** | 1 form lib + 4 animation libs + 1 routing lib | +6 |
| **structure** | 2 monorepo markers (Moon, Bazel) + 4 directory purposes (FSD: entities, features, shared, widgets) | +6 |
| **api** | tRPC detection + litestar/sanic/quart/hono hints | +5 |
| **dependencies** | 10+ category additions (tRPC, hono, elysia, panda-css, valibot, playwright, etc.) | +10 |

**Total: ~210 new detection items across 18 analyzers**

---

### Phase B: New Templates, Model Fields, Wire Unused Fields (3-4 days)

#### B1. Create missing templates
- **`dependencies.mdc.j2`** — surface dependency counts, key libraries by category, manifest/lock files
- **`cicd.mdc.j2`** — surface CI platform, build steps, deployment targets

#### B2. Wire 10+ unused fields into existing templates
| Template | Unused Fields to Wire |
|----------|-----------------------|
| `database.mdc.j2` | `orm_version` |
| `git-workflow.mdc.j2` | `release_tagging` |
| `design-system.mdc.j2` | `theme_provider` |
| `accessibility.mdc.j2` | `semantic_html_score`, `keyboard_navigation`, `color_contrast_config` |
| `performance.mdc.j2` | `bundle_size_config` |
| Remove from models: `auth.token_handling`, `auth.session_management` (never populated)

#### B3. Add ~25 new model fields
| Model | New Fields |
|-------|------------|
| `AuthResult` | `auth_strategies: list[str]`, `mfa_methods: list[str]`, `oauth_providers: list[str]`, `rate_limiting: str`, `security_headers: list[str]` |
| `DatabaseResult` | `database_types: list[str]`, `connection_pooling: str`, `schema_patterns: list[str]` |
| `ErrorHandlingResult` | `logging_frameworks: list[str]`, `structured_logging: bool`, `error_recovery_patterns: list[str]` |
| `StateManagementResult` | `state_libraries: list[str]`, `data_fetching_libraries: list[str]`, `form_library: str`, `realtime_library: str` |
| `EnvConfigResult` | `config_approaches: list[str]`, `secrets_management: str`, `kubernetes_detected: bool` |
| `GitWorkflowResult` | `codeowners_path: str`, `changelog_path: str`, `release_tool: str` |
| `DesignUIResult` | `icon_library: str`, `component_doc_tool: str`, `font_strategy: str` |
| `AccessibilityResult` | `aria_patterns: list[str]`, `form_accessibility: list[str]`, `focus_management: list[str]` |
| `PerformanceResult` | `web_vitals_monitoring: str`, `service_worker: bool`, `cdn_detected: str` |
| `TestingResult` | `api_testing_tools: list[str]`, `visual_regression: str`, `contract_testing: str`, `test_organization: str`, `snapshot_testing: bool` |
| `CICDResult` | `caching_detected: bool`, `matrix_builds: bool`, `deployment_patterns: list[str]`, `release_tool: str` |
| `I18nResult` | `message_format: str`, `rtl_languages: list[str]`, `translation_management: str` |
| `UserFlowsResult` | `dynamic_routes: list[str]`, `lazy_routes: bool` |

#### B4. Tighten `_should_generate()` guards
- `auth-patterns.mdc.j2`: require `auth_strategy` or `auth_strategies` non-empty
- `accessibility.mdc.j2`: require at least one a11y tool OR wcag_level
- `api-patterns.mdc.j2`: require `api_style` non-empty

---

### Phase C: Logic Enhancements (5-7 days)

28 logic changes, ordered by impact:

| # | Change | Analyzer | Effort |
|---|--------|----------|--------|
| C1 | **Return arrays instead of singles** (auth, database, error_handling, state_mgmt, env_config) | 5 analyzers | MEDIUM |
| C2 | Extract ORM version from package.json | database | LOW |
| C3 | Parse pyproject.toml `[project]` dependencies | dependencies | MEDIUM |
| C4 | Add Gemfile, Cargo.toml, go.mod parsing | dependencies | MEDIUM |
| C5 | Normalize version strings to semver | tech_stack, deps | LOW |
| C6 | Weight language percentages (exclude tests/config) | tech_stack | MEDIUM |
| C7 | Add OAuth provider detection (env vars + deps) | auth | MEDIUM |
| C8 | Add MFA/2FA detection (otplib, speakeasy, pyotp) | auth | LOW |
| C9 | Cookie security flags detection (HttpOnly, Secure, SameSite) | auth/security | MEDIUM |
| C10 | Parse actual linter/formatter config rules | conventions | MEDIUM |
| C11 | Detect test organization strategy (collocated vs separated) | testing | MEDIUM |
| C12 | Add icon library detection (Lucide, Heroicons, Phosphor, etc.) | design | LOW |
| C13 | Add Storybook/Histoire/Ladle detection | design | LOW |
| C14 | Detect dynamic route parameters ([id], :id) | user_flows | LOW |
| C15 | Add web vitals / performance monitoring | performance | LOW |
| C16 | Add connection pooling detection | database | LOW |
| C17 | Add schema pattern detection (UUID, soft delete, audit fields) | database | MEDIUM |
| C18 | Add structured logging detection | error_handling | LOW |
| C19 | Add form accessibility detection (label, aria-invalid, fieldset) | accessibility | MEDIUM |
| C20 | Add focus management detection (skip links, focus trap) | accessibility | MEDIUM |
| C21 | Expand ARIA to specific patterns (landmarks, live regions, etc.) | accessibility | MEDIUM |
| C22 | Add real-time library detection (Socket.IO, Pusher, Ably) | state_mgmt | LOW |
| C23 | Add translation management detection (Crowdin, Lokalise, etc.) | i18n | LOW |
| C24 | Add RTL language detection | i18n | LOW |
| C25 | Parse Dockerfile for base image + multi-stage | env_config | MEDIUM |
| C26 | Add Kubernetes/orchestration detection | env_config | LOW |
| C27 | Add error recovery patterns (retry, circuit breaker) | error_handling | MEDIUM |
| C28 | Add font strategy detection (next/font, fontsource) | design | LOW |

---

### Phase D: Anti-Pattern Detection — New Capability (4-5 days)

New cross-cutting feature: each analyzer gains an `anti_patterns: list[str]` field.

| Domain | Anti-Patterns to Flag | Severity |
|--------|----------------------|----------|
| **Security** | Hardcoded secrets, wildcard CORS, no HTTPS/HSTS, no rate limiting, no CSRF, debug mode, deprecated libs, no vuln scanning | CRITICAL-HIGH |
| **Database** | Raw SQL concatenation, missing migrations, no seed data, hardcoded connection strings, unbounded queries | CRITICAL-HIGH |
| **Testing** | No tests, no CI test step, no coverage, inverted pyramid, no E2E | CRITICAL-MEDIUM |
| **CI/CD** | No CI, no caching, no dependency automation, no security scanning | HIGH-MEDIUM |
| **Frontend** | No code splitting, missing error boundaries, no loading states | MEDIUM |
| **State** | Mixing server/client state, multiple conflicting state libs | MEDIUM |
| **Accessibility** | No a11y tools, tabIndex > 0, onClick without keyboard handler, images without alt | MEDIUM |

---

### Implementation Sequencing

```
Phase A (data) ──────────────────────────► 2-3 days
  ↓
Phase B1+B2 (templates + wire fields) ──► 1-2 days
  ↓
Phase C1 (arrays) ──────────────────────► 1-2 days
  ↓
Phase B3 (model fields as C needs them) ► 1 day
  ↓
Phase C2-C28 (incremental enhancements) ► 3-5 days
  ↓
Phase B4 (tighten guards) ─────────────► 0.5 days
  ↓
Phase D (anti-patterns) ───────────────► 4-5 days
```

**Total estimated: 12-18 days of implementation work**

---

### Research Sources

Full best-practices research is available in companion documents:
- [Auth & Security Research](2026-03-26-auth-security-research.md)
- [Database & State Management Research](2026-03-26-database-state-mgmt-research.md)
- [Testing & CI/CD Research](2026-03-26-testing-cicd-research.md)
- [Frontend, Design & Accessibility Research](2026-03-26-frontend-design-a11y-research.md)
- [DevOps, Code Quality & Infrastructure Research](2026-03-26-devops-quality-research.md)
- [Research Index](2026-03-26-analyzer-research-index.md)
