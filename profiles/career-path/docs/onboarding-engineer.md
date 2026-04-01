# career-path — Engineer Onboarding Guide

Welcome to **career-path**! This guide will help you set up Cursor with the right permissions and context for your role.

## Quick Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd career-path
   ```

2. **Install Product Builders CLI** (if not already installed):
   ```bash
   pip install product-builders
   ```

3. **Set up your Cursor environment**:
   ```bash
   product-builders setup --name "career-path" --role engineer
   ```

   This command generates:
   - `.cursor/rules/` — AI rules tailored to your role
   - `.cursor/hooks.json` — Smart guardrails (Layer 2)
   - `.cursor/cli.json` — Filesystem permissions (Layer 3)

## What You Can Do

### Your Writable Areas

**frontend_ui**: `dr-cs-frontend\components/**`, `dr-cs-frontend\pages/**`, `dr-cs-api\storage\framework\views/**`, `dr-cs-frontend\static\tarteaucitron\css/**`, `dr-cs-api\public/**`, `dr-cs-frontend\static/**`, `dr-cs-frontend\components/**`, `dr-cs-frontend\pages/**`, `dr-cs-api\storage\framework\views/**`, `dr-cs-frontend\components/**`, `dr-cs-frontend\pages/**`, `dr-cs-api\storage\framework\views/**`
**frontend_logic**: `dr-cs-frontend\store/**`, `dr-cs-frontend\store/**`
**api**: `dr-cs-frontend\api/**`, `dr-cs-api\routes/**`, `dr-cs-frontend\api/**`, `dr-cs-api\routes/**`, `dr-cs-api\routes/**`, `dr-cs-frontend\api/**`
**backend_logic**: `dr-cs-frontend\services/**`, `dr-cs-frontend\services/**`, `dr-cs-frontend\services/**`
**database**: `dr-cs-frontend\api\models/**`, `dr-cs-api\database/**`, `dr-cs-frontend\api\models/**`, `dr-cs-frontend\api\models/**`
**infrastructure**: `.gitlab/**`, `dr-cs-api\ci\docker/**`, `docker*`, `Dockerfile`, `*.yml`, `*.yaml`
**security**: `dr-cs-frontend\pages\auth/**`, `dr-cs-frontend\pages\auth/**`, `dr-cs-frontend\pages\auth/**`, `dr-cs-frontend\pages\auth/**`
**configuration**: `dr-cs-api\config/**`, `.env*`, `config/**`
**tests**: `dr-cs-api\tests/**`, `dr-cs-frontend\__tests__/**`, `dr-cs-api\specs/**`, `dr-cs-frontend\__tests__/**`
**fixtures**: `dr-cs-api\storage\framework\cache\data/**`



## Tech Stack Overview

- **Language**: TypeScript


## Getting Help

- **Cursor rules**: Check `.cursor/rules/` for project conventions
- **Questions**: Tag the engineering team in Slack/Teams
- **Blocked?**: Create a task describing what you need — the team will help

## Updating Your Setup

If the project rules change, update your local setup:

```bash
product-builders setup --name "career-path" --role engineer
```

This regenerates all rules and permissions from the latest profile.
