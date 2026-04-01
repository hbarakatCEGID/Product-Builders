# UX Improvements: Two-Step Product Setup

## Problem

The current flow from "I have a repo" to "rules are deployed" requires 7+ steps across CLI and Cursor with multiple context switches. For a platform team managing 50+ products, this is too many steps with too little guidance.

Current: `analyze` → open Cursor → deep analysis → `ingest-deep` → `generate` → enrich batches in Cursor → `export`

## Design

### The Two-Step Flow

```
Step 1:  product-builders setup-product /path/to/repo --name myapp
Step 2:  Open Cursor → @enrich-all → "run the enrichment"
```

Step 1 handles all deterministic work (analyze + generate + export).
Step 2 handles all intelligence work (Cursor rewrites rules with codebase depth).
Step 2 is optional — template rules work immediately after Step 1.

### Step 1: `setup-product` Command

**Usage:**
```bash
product-builders setup-product /path/to/repo --name myapp
product-builders setup-product /path/to/repo --name myapp --profile pm
product-builders setup-product /path/to/repo --name myapp --heuristic-only
product-builders setup-product /path/to/repo --name myapp --regenerate
```

**What it does:**
1. Validates repo path and product name
2. Runs 20 heuristic analyzers with progress bar
3. Auto-detects scopes/zones
4. Generates template rules + enrichment meta-rule
5. Exports .cursor/, docs/ to the product repo
6. Records git HEAD for drift detection

**Output UX:**
```
Setting up myapp from /path/to/repo

  Analyzing codebase ━━━━━━━━━━━━━━━━ 100%  20/20 analyzers
  Detected: TypeScript + Next.js 15 + Supabase + shadcn + Tailwind

  Generating governance
    ✓ 18 Cursor rules (.cursor/rules/)
    ✓ hooks.json (role-based access control)
    ✓ cli.json (filesystem permissions)
    ✓ Onboarding guides (5 roles)
    ✓ Enrichment meta-rule (.cursor/rules/enrich-all.mdc)

  Exported to /path/to/repo
    .cursor/rules/  (19 files)
    .cursor/hooks.json
    .cursor/cli.json
    docs/  (5 onboarding guides)

  Next step:
    1. Open /path/to/repo in Cursor
    2. Reference @enrich-all and tell Cursor to run the enrichment
    3. Cursor will rewrite rules with project-specific depth (~15 min)

    This step is optional — template rules work immediately.
```

**Design principles:**
- Progress bar, not wall of analyzer output
- One-line tech stack summary
- Clear file counts and locations
- Explicit next step with time estimate
- "Optional" reduces anxiety

**Existing commands preserved:** `analyze`, `generate`, `export` stay for power users.

**Flags:**
- `--profile <role>`: Generate role-specific governance (hooks + permissions for that role)
- `--heuristic-only`: Skip enrichment meta-rule generation
- `--regenerate`: Skip analysis, use existing profile, regenerate rules + re-export

### Step 2: `enrich-all.mdc` Self-Pacing Meta-Rule

Replaces the 4 separate `enrich-{batch}.mdc` files with ONE self-pacing meta-rule.

**Self-pacing mechanism:** The meta-rule instructs Cursor to work in 4 phases, saving files and summarizing findings after each phase. User says "continue" between phases. This prevents context window decay while keeping it to one Cursor session.

**Structure:**
```
# Enrich Rules — {product}

## What We Already Know (heuristic context)
## What We Couldn't Determine (gap-aware questions)
## Quality Requirements (cite files, DO/DON'T, word count)

## Phase 1: Critical Rules (~5 min)
  database.mdc, auth-patterns.mdc, security.mdc
  [per-rule: analyze hints + required sections]
  → Save, summarize, wait for confirmation

## Phase 2: Architecture & Conventions (~5 min)
  architecture.mdc, coding-conventions.mdc, error-handling.mdc, api-patterns.mdc
  → Save, summarize, wait for confirmation

## Phase 3: Frontend & UI (~5 min)
  design-system.mdc, frontend-patterns.mdc, user-flows.mdc, state-and-config.mdc
  → Save, summarize, wait for confirmation

## Phase 4: Supporting (~3 min)
  testing.mdc, performance.mdc, accessibility.mdc, i18n.mdc, cicd.mdc, git-workflow.mdc
  → Summarize all changes. Done.
```

**UX flow:**
1. Open Cursor in product repo
2. Say: "@enrich-all run the enrichment"
3. Cursor completes Phase 1 (3 rules), summarizes findings
4. User says "continue"
5. Repeat for Phase 2, 3, 4
6. Done — all rules are project-specific

**Why self-pacing:**
- 3-4 rules per phase avoids context decay
- Checkpoints let user review and course-correct
- User can stop after any phase (critical rules done first)
- One file to manage instead of four

## Implementation

### New files
- `src/product_builders/generators/templates/enrich-all.mdc.j2` — single enrichment meta-rule template (replaces 4 batch templates)
- CLI: `setup-product` command in `cli.py`

### Modified files
- `src/product_builders/cli.py` — add `setup-product` command
- `src/product_builders/generators/enrichment.py` — generate single `enrich-all.mdc` instead of 4 batch files
- `src/product_builders/generators/cursor_rules.py` — `_should_generate` for old batch files removed

### Removed files
- `src/product_builders/generators/templates/enrich-critical.mdc.j2`
- `src/product_builders/generators/templates/enrich-architecture.mdc.j2`
- `src/product_builders/generators/templates/enrich-frontend.mdc.j2`
- `src/product_builders/generators/templates/enrich-supporting.mdc.j2`

### What stays unchanged
- All 18+ template rules (Phase 1 improvements)
- Gap-aware deep analysis (Phase 2)
- `analyze`, `generate`, `export` commands (power user commands)
- Governance generation (hooks.json, cli.json)
- Webapp (future improvement, not this iteration)

## Verification

1. `product-builders setup-product /path/to/seeker1 --name seeker1` completes in one command
2. `.cursor/rules/enrich-all.mdc` exists in the product repo
3. All 18 template rules exist in `.cursor/rules/`
4. hooks.json, cli.json, onboarding guides exist
5. Old `enrich-{batch}.mdc` files no longer generated
6. Output shows progress bar + tech summary + clear next step
7. `product-builders setup-product --help` shows all options
8. `--regenerate` skips analysis and uses existing profile
9. 245+ tests pass
