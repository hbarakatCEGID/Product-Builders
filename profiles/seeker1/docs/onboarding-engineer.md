# seeker1 — Engineer Onboarding Guide

Welcome to **seeker1**! This guide will help you set up Cursor with the right permissions and context for your role.

## Quick Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd seeker1
   ```

2. **Install Product Builders CLI** (if not already installed):
   ```bash
   pip install product-builders
   ```

3. **Set up your Cursor environment**:
   ```bash
   product-builders setup --name "seeker1" --role engineer
   ```

   This command generates:
   - `.cursor/rules/` — AI rules tailored to your role
   - `.cursor/hooks.json` — Smart guardrails (Layer 2)
   - `.cursor/cli.json` — Filesystem permissions (Layer 3)

## What You Can Do

### Your Writable Areas

**frontend_ui**: `src/components/**`, `src\components/**`, `src/components/**`
**api**: `src\app\api/**`, `src/app/api/**`, `src\app\api/**`
**backend_logic**: `src/lib/**`, `src\lib/**`, `src/lib/**`
**database**: `supabase\migrations/**`
**configuration**: `.env*`, `config/**`
**tests**: `src\lib\pipeline\__tests__/**`, `src\lib\pipeline\__tests__/**`



## Tech Stack Overview

- **Language**: TypeScript
- **Frameworks**: next, react
- **Auth**: supabase


## Getting Help

- **Cursor rules**: Check `.cursor/rules/` for project conventions
- **Questions**: Tag the engineering team in Slack/Teams
- **Blocked?**: Create a task describing what you need — the team will help

## Updating Your Setup

If the project rules change, update your local setup:

```bash
product-builders setup --name "seeker1" --role engineer
```

This regenerates all rules and permissions from the latest profile.
