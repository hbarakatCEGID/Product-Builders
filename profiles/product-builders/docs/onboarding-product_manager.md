# product-builders — Product Manager Onboarding Guide

Welcome to **product-builders**! This guide will help you set up Cursor with the right permissions and context for your role.

## Quick Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd product-builders
   ```

2. **Install Product Builders CLI** (if not already installed):
   ```bash
   pip install product-builders
   ```

3. **Set up your Cursor environment**:
   ```bash
   product-builders setup --name "product-builders" --role product_manager
   ```

   This command generates:
   - `.cursor/rules/` — AI rules tailored to your role
   - `.cursor/hooks.json` — Smart guardrails (Layer 2)
   - `.cursor/cli.json` — Filesystem permissions (Layer 3)

## What You Can Do



### Restricted Areas

These areas are not accessible for your role:

- **configuration**

If you need changes in restricted areas, create a task in Jira/Linear with clear requirements.

## Tech Stack Overview

- **Language**: Python
- **Frameworks**: fastapi

## Commands to Avoid

The following commands are blocked for your role because they can affect production:

- `prisma:migrate`
- `prisma:db push`
- `alembic upgrade`
- `alembic downgrade`
- `flyway migrate`
- `npm publish`
- `yarn publish`
- `docker build`
- `docker push`
- `rm -rf`
- `git push --force`
- `git push -f`
- `git reset --hard`

If you need to run any of these, ask the engineering team.

## Getting Help

- **Cursor rules**: Check `.cursor/rules/` for project conventions
- **Questions**: Tag the engineering team in Slack/Teams
- **Blocked?**: Create a task describing what you need — the team will help

## Updating Your Setup

If the project rules change, update your local setup:

```bash
product-builders setup --name "product-builders" --role product_manager
```

This regenerates all rules and permissions from the latest profile.
