# Prompt: Generate Stakeholder Overview Presentation

> **How to use this document:** Copy the entire content below into Claude (or another LLM) and ask it to generate a polished slide deck. All facts, numbers, and framing are included — the LLM should not invent or assume any data.

---

## Instructions for the LLM

Create a professional presentation slide deck for a stakeholder audience. The presentation should be visually clean, business-focused, and use minimal technical jargon. Target 15-18 slides. Use clear headings, short bullet points, and tables where appropriate. Do not include code snippets — this is a business audience.

**Audience:** Leadership, product directors, PMs who may become early adopters.

**Goal:** Secure buy-in for a pilot program. Get decisions on: which products to pilot (DP-3), pilot timeline (DP-4), design system integration strategy (DP-7), and PM support model (DP-8).

**Tone:** Confident, practical, outcome-focused. Not a sales pitch — a clear proposal backed by research.

**Format:** One slide per section below. Use the section headings as slide titles (adjust for readability). Keep bullet points concise (max 6-8 per slide). Use tables for comparisons.

---

## Slide 1: Title

**Product Builders**
Enabling Product Teams to Contribute Code Safely via AI

March 2026

---

## Slide 2: The Challenge

- We have **50+ products** across diverse tech stacks: React, Java Spring, Python Django, .NET, and more
- They run on mixed Git platforms (GitHub, GitLab, Azure DevOps, Bitbucket)
- **Product managers, designers, and QA** want to contribute features directly — not just spec them and wait
- **Cursor AI** can generate code, but without guardrails it doesn't know each product's architecture, conventions, or safety rules
- Unconstrained AI code **breaks CI, violates patterns, introduces security risks, and creates rework for engineers**
- Today, engineers must rewrite AI-generated code from scratch — defeating the purpose

---

## Slide 3: The Opportunity

- **Reduce engineering bottleneck** for product-led features (UI improvements, copy changes, style updates, translations)
- **Accelerate time-to-market** — PMs ship features themselves instead of waiting in the sprint backlog
- **Scale contribution** without proportional engineering headcount growth
- **Maintain code quality and security** — AI follows the same patterns engineers use
- **No new infrastructure required** — the solution uses tools teams already have (Cursor, Git)

---

## Slide 4: What We're Building

Two deliverables:

**1. CLI Tool (Python)**
- Automatically analyzes any product codebase across 18 dimensions (tech stack, database, auth, conventions, dependencies, etc.)
- Generates tailored AI rules (14 files), safety hooks, and filesystem permissions — all specific to that product
- One-time setup per product, approximately 15 minutes
- Runs fully locally — no external AI APIs, no additional cost

**2. Web Application**
- Documentation and getting-started guides
- Per-role onboarding (PM, Designer, Engineer, QA, Technical PM)
- CLI download and installation page
- Product catalog showing analyzed products and their tech stack

---

## Slide 5: How It Works — The Big Picture

Present this as a simple left-to-right visual flow (no code):

**Inputs:** Product codebase (local clone) + company-wide standards + contributor profile (PM, Designer, etc.)

**Process:** Product Builders CLI analyzes the codebase across 18 dimensions automatically

**Outputs:**
- 14 AI rule files tailored to the product (tech stack, database safety, auth patterns, coding conventions, etc.)
- Safety hooks that block dangerous operations with helpful messages
- Filesystem permissions that physically prevent access to restricted areas
- Onboarding guide for the contributor

**Key message:** Analyze once → generate rules → every contributor benefits. Rules stay in the product repo and auto-load when anyone opens it in Cursor.

---

## Slide 6: The PM Experience — Before and After

Present as a two-column comparison table:

| Without Product Builders | With Product Builders |
|---|---|
| PM asks AI for a feature | PM asks AI for a feature |
| AI generates generic code | AI generates **product-compatible** code |
| Code fails CI, uses wrong patterns | Code follows existing patterns and passes CI |
| Engineer rewrites it from scratch | Engineer reviews and approves |
| PM gives up after 2 failed attempts | PM ships features independently |
| No guardrails — AI can touch anything | Three-layer safety prevents dangerous changes |

---

## Slide 7: The PM Experience — Day-to-Day

**Getting Started (one-time, 5 minutes):**
1. Clone the product repo
2. Run one command: `product-builders setup --profile pm`
3. Open Cursor — done. Rules and safety auto-load.

**Day-to-Day Workflow:**
1. PM opens Cursor and describes what they want: "Add user preferences feature"
2. The AI already knows: which framework and components to use, which files the PM can touch, which patterns to follow, and when to redirect to engineering
3. AI generates compatible code
4. PM creates a pull request
5. AI reviewer checks compliance, then developer reviews and approves

**First Contribution:**
- A pre-built "Hello World" task walks the PM through the entire flow end-to-end with zero risk
- Start with low-risk tasks (copy changes, style tweaks), then graduate to feature work

---

## Slide 8: Safety — Three Layers of Defense

Present as three stacked layers, from lightest to strictest:

**Layer 1 — Rules (Soft Guidance)**
- AI is told the contributor's scope and the product's patterns
- Example: "You may only modify files in src/components/ and src/pages/"
- AI usually follows this. But it's not enforced.

**Layer 2 — Hooks (Smart Blocking)**
- If AI tries to edit a restricted file, it is **blocked with a helpful message**
- Example: "This is a database migration. Database changes need engineering. Want me to create a Jira issue instead?"
- Validated in Feb 2026 — Cursor's preToolUse hook supports this pattern

**Layer 3 — Permissions (Hard Deny)**
- Physical filesystem restrictions via Cursor's CLI permissions system
- Even if Layers 1-2 fail, the AI **cannot** access restricted paths
- Last line of defense — guarantees enforcement

**Key message:** Defense in depth. The AI is redirected helpfully — not just rejected.

---

## Slide 9: Graceful Boundaries — Redirect, Not Reject

When a PM asks for something outside their scope, the AI **helps them find the right path**:

**Example interaction:**

> **PM:** "Add a new database table for user preferences"
>
> **AI:** "Database schema changes are outside your scope for this product and need engineering involvement. I can help you in two ways:
> 1. Draft a Jira issue describing the table you need (columns, relationships, constraints)
> 2. Build the frontend components that will USE the preferences once the table exists
>
> Which would you like?"

**Philosophy:** The AI is a collaborator, not a gatekeeper. Every blocked action offers a constructive alternative.

---

## Slide 10: Five Contributor Profiles

Present as a table:

| Profile | Can Write | Read-Only | Blocked |
|---|---|---|---|
| **Engineer** | Everything | — | — |
| **Technical PM** | Frontend + API | Backend, Tests | Database, Infra, Security |
| **Product Manager** | Frontend only | API, Backend | Database, Infra, Security |
| **Designer** | UI components only | Frontend logic | Everything else |
| **QA / Tester** | Tests only | All production code | Database, Infra, Security |

- Each product team **customizes** these defaults via a simple configuration file (scopes.yaml)
- Profile is assigned when the contributor runs the setup command — governance is local and personalized
- Rules (product knowledge) are shared via Git — same for everyone
- Hooks and permissions are local and gitignored — personalized per contributor

---

## Slide 11: What the AI Learns About Each Product

The CLI analyzes **18 dimensions** — everything that causes AI-generated code to break:

**Critical (can cause data loss or security breaches):**
- Tech stack (languages, frameworks, versions)
- Database and ORM (migration safety, schema conventions)
- Authentication and authorization (auth patterns, token handling)

**High Impact (breaks production functionality):**
- Dependencies, error handling, i18n/l10n, state management, environment config, Git workflow

**Medium Impact (quality and compliance):**
- Project structure, coding conventions, security patterns, testing, CI/CD, design/UI, accessibility, API patterns, performance

**Deep Analysis (via Cursor itself — too nuanced for automated detection):**
- Architecture and module boundaries, domain model and business logic, implicit conventions

---

## Slide 12: Rollout Strategy

Present as a phased timeline:

**Phase 1-3: Build + Pilot (first deliverable)**
- CLI foundation + 8 core analyzers + rule generation + three-layer governance
- Web app with documentation and onboarding guides
- Pilot with 2-3 selected products and 2-3 PMs per product
- Validate the 80% first-attempt pass rate target

**Phase 4: Scale**
- Remaining 10 analyzers (security, testing, CI/CD, design system, accessibility, API, i18n, state management, environment, performance)
- Roll out to more products based on pilot results

**Phase 5: Automation and Lifecycle**
- Automated drift detection: are rules still accurate after product updates?
- Feedback system: developers flag inaccurate rules during PR review
- Lifecycle management at scale for 50+ products
- Metrics and observability (PR pass rates, rule effectiveness)

**Principle:** Build for scale, test with pilot first. Each phase ships value independently.

---

## Slide 13: What We Need From You

Present as a table of clear asks:

| # | Decision | What We Need | Impact |
|---|---|---|---|
| **DP-3** | Pilot Product Selection | Which 2-3 products to pilot with? Ideal: one simple frontend-only, one full-stack with database, one using shared components | Determines analyzer priority and pilot scope |
| **DP-4** | Pilot Timeline | Start date, duration (recommend 4-6 weeks), success criteria for scaling | Planning and resource allocation |
| **DP-7** | Design System Strategy | Which design systems exist? Which products should adopt which DS? Should the DS team participate in maintaining rules? | Affects Phase 4 design analyzer depth |
| **DP-8** | PM Support Model | When a PM gets stuck, who do they ask? Options: dedicated Slack channel, buddy system (one engineer per PM), office hours, FAQ, or a combination | Critical for adoption — first 2 weeks make or break it |

**Note:** Other decisions (shared library inventory, AI review tool, zone definitions, staleness thresholds, Cursor Enterprise) are engineering-internal and don't need stakeholder input.

---

## Slide 14: Success Metric

**PM-authored PRs pass CI and AI review on first attempt at 80%+ rate**

What this means:
- 8 out of 10 PR submissions by PMs require zero rework
- The AI-generated code is compatible with the product on the first try
- Engineers spend time reviewing business logic and edge cases — not rewriting boilerplate

How we measure it:
- Track during pilot: number of PM PRs, first-attempt pass rate, common failure reasons
- Feedback loop: developers flag inaccurate rules, fed into next regeneration cycle

---

## Slide 15: Long-Term Vision

**Today:** CLI + Web App (local rules, per-product setup)

**Tomorrow:** MCP-Native Platform

- **Zero-friction onboarding** — no local setup at all; connect to a server and start working
- **Multi-IDE support** — same rules work in Cursor, Claude Code, Windsurf, and future MCP-compatible IDEs
- **Centralized governance** — profiles managed server-side; a PM physically cannot access engineer tools
- **Real-time rule updates** — change a rule on the server, every active session picks it up immediately
- **Analytics** — adoption metrics, PR pass rates, rule effectiveness across all products

**Key message:** The current architecture evolves toward this — no rewrite needed. CLI analyzers become the Core Engine; the webapp becomes the Admin Portal; the MCP Gateway is the new addition.

**Prerequisites:** MCP authorization spec must be stable; CLI + webapp must be proven with pilot first.

---

## Slide 16: Risk Management

Present as a table:

| Risk | Mitigation |
|---|---|
| PM adoption lower than expected | Guided first contribution ("Hello World" task), buddy system, low-risk starting tasks, trust-building progression |
| AI-generated code doesn't meet 80% target | Rule validation and smoke testing, deep analysis review step, feedback loop, manual overrides system |
| Engineer resistance to PM-authored PRs | Address in pilot retrospective; executive sponsorship if needed |
| Rules become stale after product updates | Automated drift detection, CI integration, scheduled scans across all products |
| Cursor API changes break hooks | Version compatibility layer, feature detection, regression tests after each Cursor release |
| Scope creep (18 analyzers + DS + webapp) | Incremental delivery — build and ship phase by phase; MVP is Phase 1-3 for pilot |

---

## Slide 17: Why This Matters

- **50+ products.** Dozens of potential contributors. One system to make it safe.
- Reduces the engineering bottleneck for product-led features
- Accelerates time-to-market for UI/UX improvements
- Scales the contribution model without proportional headcount growth
- Maintains code quality — AI follows the same patterns engineers use
- **No new infrastructure** — uses tools teams already have
- **No external AI APIs** — zero additional cost

---

## Slide 18: Next Steps

1. **Select pilot products** (DP-3) — identify 2-3 candidates with different complexity levels
2. **Define pilot timeline** (DP-4) — start date, 4-6 week duration, success criteria
3. **Identify pilot PMs** — who will participate in the pilot?
4. **Define PM support model** (DP-8) — Slack channel, buddy system, office hours, or combination?
5. **Engineering kickoff** — Phase 1 implementation begins immediately
6. **Design system inventory** (DP-7) — catalog existing design systems and hosting locations

---

## Appendix Slide: No Cursor Enterprise Required

All governance uses **project-level files** committed to each product repository:
- `.cursor/rules/` — 14 AI rule files
- `.cursor/hooks.json` — safety hooks with helpful blocking messages
- `.cursor/cli.json` — hard filesystem permissions

This works regardless of Cursor licensing. No dependency on Cursor Enterprise dashboard.

If Cursor Enterprise becomes available later, its features are **additive**:
- Enforced Team Rules (cannot be disabled)
- Sandbox Mode
- Audit Logs
- Background Agent API for bulk automation

---

## Appendix Slide: Zero External Dependencies

| Component | How It Runs |
|---|---|
| Heuristic analysis (18 analyzers) | Fully local and offline |
| Deep analysis (architecture, domain, conventions) | Cursor itself — no external LLM API keys |
| Rule generation (14 .mdc files) | Local Jinja2 templates |
| Safety hooks | Local shell scripts |
| Governance (hooks + permissions) | Project-level files, no server |

**No LLM API keys. No new infrastructure. No additional cost.**
The only requirement is Cursor, which teams already use.
