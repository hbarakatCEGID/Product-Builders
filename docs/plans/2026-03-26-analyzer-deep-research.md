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

## PRIORITIZED ACTION PLAN

### Tier 1: Quick Wins (LOW effort, HIGH impact)

1. **Create `dependencies.mdc.j2` and `cicd.mdc.j2` templates** — 2 dimensions currently produce dead data
2. **Return arrays instead of single values** for: auth_strategies, state_libraries, data_fetching_libraries, logging_frameworks, config_approaches, database types
3. **Wire unused fields into templates** or remove them (10+ wasted fields)
4. **Add 10+ missing frameworks** to tech_stack (Astro, Hono, Litestar, Phoenix, etc.)
5. **Add CODEOWNERS detection** to git_workflow
6. **Add MFA/2FA detection** to auth (scan for totp, authenticator deps)
7. **Tighten `_should_generate()`** for auth-patterns, accessibility, api-patterns

### Tier 2: Medium Effort, High Value

8. **Extract ORM versions** from package.json/lock files
9. **Parse pyproject.toml dependencies** properly (currently skipped)
10. **Add OAuth provider detection** (Google, GitHub, Microsoft configs)
11. **Add structured logging detection** (JSON logs, OpenTelemetry)
12. **Normalize version strings** to semver across all analyzers
13. **Weight language percentages** (exclude tests/config/docs from counts)
14. **Parse actual linter/formatter config rules** in conventions analyzer
15. **Detect test organization** (unit/integration/e2e directory separation)

### Tier 3: Higher Effort, Medium Value

16. **Return composite database stacks** (PostgreSQL + Redis + MongoDB)
17. **Add cookie security flags** detection to auth
18. **Parse OpenAPI specs** for API endpoint details
19. **Add web vitals/performance budget** detection
20. **Add Storybook/component documentation** detection
21. **Detect dynamic route parameters** ([id], :id) in user flows
22. **Add error recovery pattern** detection (retry, circuit breaker)
23. **Parse Dockerfile** for base image, multi-stage builds
24. **Add form accessibility** detection (label-input associations)

### Tier 4: Future Enhancements

25. **Transitive dependency analysis** from lock files
26. **Translation completeness metrics** per locale
27. **Route protection coverage** estimate (% of routes protected)
28. **Error hierarchy extraction** (class X extends Y via AST)
29. **Build matrix detection** from CI/CD workflows
30. **Color palette extraction** from design tokens
