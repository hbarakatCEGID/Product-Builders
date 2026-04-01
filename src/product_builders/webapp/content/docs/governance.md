# Governance model (three layers)

Generated governance stacks three complementary mechanisms:

## Layer 1 — Rules (`.mdc`)

Soft guidance for the AI: stack, conventions, security, testing, contributor scopes, etc.  
Templates are Jinja2-driven from the `ProductProfile`.

## Layer 2 — Hooks (`hooks.json`)

**Smart blocking** of dangerous operations (`preToolUse`, `beforeShellExecution`) with clear messages — not a full sandbox, but high-signal guardrails.

Blocked commands are **filtered by the project's actual tech stack**: tool-specific commands (e.g., `prisma migrate`, `drizzle push`) are only blocked when that tool is detected as a dependency. This avoids false-positive blocks for tools not present in the project.

## Layer 3 — Permissions (`cli.json`)

**Hard** filesystem allow/deny rules for the Cursor CLI — strongest enforcement layer.

## Scopes

`scopes.yaml` defines **zones** (directory globs) and what each **contributor role** may read, write, or must avoid. Generators use this for rules and onboarding.

## Analysis Intelligence

Governance accuracy depends on the quality of analysis. Product Builders supports three layers of analysis intelligence:

1. **Heuristic analysis** (always) — file existence, dependency manifests, regex patterns, config parsing
2. **AST pre-pass** (default install; degrades gracefully if tree-sitter is unavailable) — tree-sitter parses TypeScript, JavaScript, and Python for imports, exports, definitions, decorators, and components
3. **Cursor-assisted deep analysis** (optional) — adaptive bootstrap prompts guide Cursor through architecture, domain model, and convention analysis; results are merged via `ingest-deep`

Each layer enriches the `ProductProfile`, which drives all generated governance artifacts.

---

See **docs/HOOKS_RESEARCH.md** in the repo for hook semantics and platform limits.
