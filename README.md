# Product Builders

**Product Builders** analyzes product repositories and generates tailored [Cursor](https://cursor.com) governance: rules (`.mdc`), hooks (`hooks.json`), CLI permissions (`cli.json`), onboarding guides, and scopes. The goal is to let PMs, designers, QA, and engineers work with AI assistants **without bypassing** each product's architecture, security boundaries, or conventions.

---

## Two-step setup

```bash
# Step 1: Analyze, generate rules, and export to the product repo
product-builders setup-product /path/to/repo --name myapp

# Step 2 (optional): Open in Cursor, reference @enrich-all
# Cursor rewrites template rules with project-specific depth (~15 min)
```

That's it. Template rules work immediately after Step 1. Step 2 adds project-specific DO/DON'T examples, anti-patterns, and file-path references by leveraging Cursor's codebase understanding.

---

## What you get


| Output                                      | Purpose                                                                                                              |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Heuristic profile** (`analysis.json`)     | Structured snapshot of stack, DB, auth, errors, security, tests, CI/CD, BaaS, component libraries, and 20 dimensions |
| **Cursor rules** (`.cursor/rules/*.mdc`)    | Product-specific guidance for the AI (18+ rules covering all dimensions)                                             |
| **Enrichment meta-rule** (`enrich-all.mdc`) | Self-pacing instructions for Cursor to rewrite rules with project-specific depth                                     |
| **Hooks** (`.cursor/hooks.json`)            | Layer 2: contextual blocking with messages (e.g. read-only zones)                                                    |
| **Permissions** (`.cursor/cli.json`)        | Layer 3: hard deny for paths/commands per role                                                                       |
| `**scopes.yaml`**                           | Single source of truth for zones -- drives all three governance layers                                               |
| **Onboarding & checklist**                  | Role-specific docs and CI-friendly review checklist                                                                  |


### How rules get project-specific

1. **Heuristic analysis** (offline, ~2 min) -- 20 analyzers detect tech stack, database, auth, conventions, and more
2. **Template generation** -- Jinja2 templates render rules using detected data as fallback
3. **Cursor enrichment** (optional, ~15 min) -- A self-pacing meta-rule instructs Cursor to rewrite rules with real code examples, anti-patterns, and file-path citations from the actual codebase

The enrichment meta-rule works in 4 phases to prevent context window decay:

- **Phase 1: Critical** -- database, auth, security
- **Phase 2: Architecture** -- architecture, conventions, error handling, API
- **Phase 3: Frontend** -- design system, frontend patterns, routes, state
- **Phase 4: Supporting** -- testing, performance, accessibility, i18n, CI/CD, git

### Gap-aware analysis

The enrichment meta-rule includes **gap-aware questions** -- instead of generic prompts like "What's your architecture pattern?", it references what heuristics detected and asks about what's missing: "We detected PostgreSQL via Supabase but no ORM. How does the project query the database?"

---

## Requirements

- **Python 3.11+** (`>=3.11,<4.0`)
- **Git** (optional -- used for drift detection)

---

## Installation

```bash
pip install -e .
```

This installs the CLI, web app stack (FastAPI, uvicorn), tree-sitter AST support, and dev tooling (pytest, ruff, mypy).

---

## Typical workflow

### For platform teams (setting up products)

```bash
# One command: analyze + generate + export
product-builders setup-product /path/to/repo --name myapp

# With role-specific governance:
product-builders setup-product /path/to/repo --name myapp --profile pm

# Regenerate without re-analyzing:
product-builders setup-product /path/to/repo --name myapp --regenerate
```

Then optionally open the repo in Cursor and reference `@enrich-all` for deeper rules.

### For contributors (using the product)

```bash
git clone <product-repo>
cd product-repo

# Install role-specific governance locally
product-builders setup --name myapp --profile pm

# Open Cursor and start working
cursor .
```

### Bulk operations

```bash
product-builders bulk-analyze --manifest products.yaml
product-builders bulk-analyze --monorepo /path/to/monorepo
```

### Lifecycle

```bash
product-builders check-drift --name myapp --repo /path/to/repo
product-builders check-drift --name myapp --repo /path/to/repo --full
product-builders feedback --name myapp --rule database --issue "ORM hint wrong"
product-builders metrics --name myapp
```

---

## CLI reference


| Command             | Description                                               | Key options                                                                          |
| ------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `**setup-product**` | **Recommended.** Analyze + generate + export in one step. | `REPO_PATH` (arg), `-n, --name`, `-p, --profile`, `--heuristic-only`, `--regenerate` |
| `**analyze`**       | Run heuristic analyzers on a product repo.                | `-n, --name`, `--heuristic-only`, `--sub-project`                                    |
| `**generate`**      | Regenerate rules from a cached profile.                   | `-n, --name`, `-p, --profile`, `--validate`                                          |
| `**export**`        | Copy rules/hooks/permissions to a product repo.           | `-n, --name`, `-t, --target`, `-p, --profile`                                        |
| `**setup**`         | Install role-specific governance in current directory.    | `-n, --name`, `-p, --profile` (required)                                             |
| `**ingest-deep**`   | Merge Cursor-produced deep analysis into profile.         | `-n, --name`, `-r, --repo`, `--deep-file`, `--dry-run`                               |
| `**list**`          | List all analyzed products.                               | --                                                                                   |
| `**bulk-analyze**`  | Analyze multiple repos from manifest or monorepo.         | `--manifest`, `--monorepo`                                                           |
| `**check-drift**`   | Detect stale rules vs. current codebase.                  | `-n, --name`, `-r, --repo`, `--full`                                                 |
| `**metrics**`       | Show recent metrics events.                               | `-n, --name`, `--limit`                                                              |
| `**feedback**`      | Record rule accuracy feedback.                            | `-n, --name`, `-r, --rule`, `-i, --issue`                                            |
| `**wizard**`        | Interactive walkthrough of all phases.                    | `--phase`, `-y`, `--repo`, `-n`, `-p`, `--validate`                                  |


Role aliases: `engineer`, `eng`, `pm`, `product_manager`, `designer`, `qa`, `qa_tester`, `tester`, `technical-pm`, `technical_pm`, `tech_pm`.

---

## Governance layers

1. **Rules (soft)** -- `.mdc` files teach the AI what patterns to follow
2. **Hooks (smart block)** -- `hooks.json` intercepts edits with helpful messages
3. **Permissions (hard deny)** -- `cli.json` enforces filesystem boundaries

`**scopes.yaml`** maps zones (e.g. `frontend_ui`, `database`) to glob patterns and defines what each role can access.

### Contributor roles


| Role                | Can edit        | Read-only              | Forbidden        |
| ------------------- | --------------- | ---------------------- | ---------------- |
| **Engineer**        | Everything      | --                     | --               |
| **Technical PM**    | Frontend + API  | Backend                | DB, Infra        |
| **Product Manager** | Frontend UI     | API, Backend           | DB, Infra        |
| **Designer**        | UI/CSS          | Frontend logic         | API, Backend, DB |
| **QA/Tester**       | Tests, Fixtures | Frontend, API, Backend | DB, Infra        |


---

## Configuration


| Variable           | Purpose                | Default                       |
| ------------------ | ---------------------- | ----------------------------- |
| `PB_HOME`          | Root for default paths | Package parent directory      |
| `PB_PROFILES_DIR`  | Profile directories    | `{PB_HOME}/profiles`          |
| `PB_STANDARDS_DIR` | Company standards YAML | `{PB_HOME}/company_standards` |


---

## Web application

The web UI is a **FastAPI** app: in-browser docs, a catalog of analyzed products (under your profiles directory), role onboarding pages, and an **Operations** dashboard that can run CLI jobs and stream logs.

### Prerequisites

Same as [Installation](#installation): Python 3.11+, package installed in editable mode so `uvicorn` and templates are available.

```bash
cd /path/to/Product-Builders
pip install -e .
```

### Start the server

From the repository root (or any directory where the package is installed):

```bash
# Recommended for local development (auto-reload on code changes)
product-builders-web --reload
```

Equivalent ways to start:

```bash
python -m product_builders.webapp --reload
uvicorn product_builders.webapp.app:app --host 127.0.0.1 --port 8000 --reload
```

Then open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

| Option        | Default       | Description                          |
| ------------- | ------------- | ------------------------------------ |
| `--host`      | `127.0.0.1`   | Bind address                         |
| `--port`      | `8000`        | TCP port                             |
| `--reload`    | off           | Restart server when source files change (development) |

Stop the server with **Ctrl+C** in the terminal.

For a quick production-style run (no reload), omit `--reload`:

```bash
product-builders-web --host 0.0.0.0 --port 8000
```

### Using the UI

- **Landing (`/`)** — Overview and entry points into the app.
- **Download (`/download`)** — How to install the CLI for contributors.
- **Documentation (`/docs`, `/docs/{slug}`)** — Packaged guides (getting started, CLI, governance, etc.).
- **Products (`/products`)** — Lists products that have a folder under your configured profiles directory (see [Configuration](#configuration)). Run `product-builders setup-product` or `analyze` first so profiles exist; otherwise the catalog may be empty.
- **Product detail (`/products/{name}`)** — Summary and links to onboarding per role.
- **Onboarding (`/products/{name}/onboarding/{role}`)** — Rendered markdown onboarding for that role.
- **Operations (`/operations`)** — Run selected CLI workflows from the browser with live log output.

**OpenAPI / Swagger** for the HTTP API is at **[http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)**.

### Quick reference (routes)

| Page                                 | Purpose                                          |
| ------------------------------------ | ------------------------------------------------ |
| `/`                                  | Landing page                                     |
| `/download`                          | Installation instructions                        |
| `/docs`                              | Documentation                                    |
| `/products`                          | Product catalog                                  |
| `/products/{name}`                   | Product detail + onboarding links                |
| `/products/{name}/onboarding/{role}` | Role-specific onboarding guide                   |
| `/operations`                        | Operations dashboard (run commands from browser) |
| `/api/docs`                          | Swagger UI (REST API)                            |


---

## Development

```bash
pip install -e .
pytest tests -q
ruff check src tests
```

