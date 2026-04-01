# Getting started

Product Builders turns a repository into **Cursor rules**, **hooks**, **CLI permissions**, and **onboarding guides** -- so AI agents and contributors share the same guardrails.

## Two-step setup

### Step 1: Analyze, generate, and export

```bash
product-builders setup-product /path/to/repo --name my-product
```

This single command:
1. Runs 20 heuristic analyzers (offline, ~2 min)
2. Generates 18+ Cursor rules, hooks, permissions, and onboarding guides
3. Exports everything to the product repo

Template rules work immediately after this step.

### Step 2: Cursor enrichment (optional)

1. Open the product repo in Cursor
2. Reference `@enrich-all` and tell Cursor to run the enrichment
3. Cursor rewrites template rules with project-specific depth (~15 min)

Cursor works through 4 phases:
- **Critical** -- database, auth, security
- **Architecture** -- architecture, conventions, error handling, API patterns
- **Frontend** -- design system, frontend patterns, routes, state management
- **Supporting** -- testing, performance, accessibility, i18n, CI/CD, git workflow

After each phase, Cursor summarizes what it found. Say "continue" to proceed.

### Gap-aware analysis

The enrichment meta-rule includes **gap-aware questions** that reference what heuristics detected and target what's missing. Instead of generic "What's your architecture pattern?", it asks: "We detected PostgreSQL via Supabase but no ORM. How does the project query the database?"

## Install

```bash
pip install -e .
pip install -e ".[webapp]"   # optional: this documentation server
```

## Individual commands (power users)

If you need granular control, the individual commands are still available:

```bash
product-builders analyze /path/to/repo --name my-product
product-builders generate --name my-product
product-builders export --name my-product --target /path/to/repo
```

## Contributor setup

After the platform team exports rules to the product repo:

```bash
git clone <product-repo>
cd product-repo
product-builders setup --name my-product --profile pm
cursor .
```

The PM gets role-specific rules, hooks (smart blocking), and permissions (hard deny). When they try to edit a database migration, Cursor shows: "This requires engineering involvement."

## Profiles

Generated artifacts live under `profiles/<name>/`. The **catalog** lists every profile on this server.
