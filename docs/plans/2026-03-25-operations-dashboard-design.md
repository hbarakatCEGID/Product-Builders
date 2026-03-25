# Operations Dashboard & Executable API Design

**Date:** 2026-03-25
**Status:** Approved
**Approach:** FastAPI + WebSocket + htmx (Approach B)

---

## Summary

Enrich the Product Builders webapp so that CLI commands can be executed directly from the browser. This adds:

1. **New POST API endpoints** mirroring each CLI command (appear in Swagger at `/api/docs`)
2. **WebSocket real-time streaming** of command output
3. **Operations dashboard** (`/operations`) with tabbed command forms and a terminal viewer
4. **Contextual buttons** on existing product/catalog pages for common actions

## Decisions

- **One job at a time** — new requests while one is running return 409 Conflict
- **Real-time output** via WebSocket (subprocess stdout/stderr streamed line by line)
- **Recent paths** remembered in `PB_HOME/recent_paths.json` (last 10 unique)
- **htmx** for form/tab interactivity (CDN, no build step)
- **~80 lines vanilla JS** for WebSocket terminal handler
- **CLI code untouched** — web layer spawns CLI as subprocess

## API Endpoints

| Method | Path | Body | Description |
|--------|------|------|-------------|
| POST | `/api/analyze` | `{repo_path, name, heuristic_only?, sub_project?}` | Start analysis |
| POST | `/api/generate` | `{name, profile?, validate?}` | Generate rules/governance |
| POST | `/api/export` | `{name, target, profile?}` | Export artifacts to repo |
| POST | `/api/setup` | `{name, profile}` | Setup governance in target dir |
| POST | `/api/check-drift` | `{name, repo_path, full?}` | Check profile drift |
| POST | `/api/feedback` | `{name, rule, issue}` | Record feedback |
| GET | `/api/metrics/{name}` | query: `limit?` | Get metrics events |
| GET | `/api/recent-paths` | — | Get recently used paths |
| WS | `/ws/execute` | query: `job_id` | Real-time command output |

## WebSocket Protocol

**Server -> Client messages:**

```json
{"type": "log", "line": "Running tech_stack analyzer...", "stream": "stdout"}
{"type": "log", "line": "Warning: no package.json found", "stream": "stderr"}
{"type": "status", "status": "running"}
{"type": "done", "status": "completed", "exit_code": 0, "duration_s": 4.2}
{"type": "done", "status": "failed", "exit_code": 1, "error": "Product not found"}
```

**Implementation:** Spawn CLI as subprocess via `asyncio.create_subprocess_exec`, capture stdout/stderr line by line, push to WebSocket. Lines buffered in Job object for reconnection.

## Job Model

```python
@dataclass
class Job:
    id: str
    command: str
    args: dict
    status: "queued" | "running" | "completed" | "failed"
    output_lines: list[str]
    started_at: datetime
    finished_at: datetime | None
```

## Operations Dashboard (`/operations`)

Tabbed interface with one form per command:

- **Tabs:** Analyze | Generate | Export | Setup | Check Drift | Feedback
- **Forms:** htmx-swapped partials per tab via `hx-get="/partials/form/{command}"`
- **Terminal:** Dark console div, monospace, auto-scroll, stderr in red
- **Recent paths:** Dropdown populated via `/api/recent-paths` on input focus
- **Product names:** Dropdown populated from `/api/products`

### Form Fields

| Command | Fields |
|---------|--------|
| Analyze | repo_path*, name*, heuristic_only, sub_project |
| Generate | name*, profile (dropdown), validate |
| Export | name*, target*, profile (dropdown) |
| Setup | name*, profile* (dropdown) |
| Check Drift | name*, repo_path*, full |
| Feedback | name*, rule*, issue* |

## Contextual Buttons

**Product detail page (`/products/{name}`):**
- Re-analyze (inline form for repo_path)
- Regenerate Rules (direct run)
- Check Drift (inline form for repo_path)

**Catalog page (`/products`):**
- "Analyze New Product" button -> links to `/operations`
- Per-row refresh icon -> links to `/operations?command=analyze&name={product}`

Inline actions use a shared `partials/inline_terminal.html` component.

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `webapp/routes_api.py` | API router: POST endpoints + WebSocket |
| `webapp/job_manager.py` | Job dataclass, queue, subprocess runner, recent paths |
| `webapp/templates/operations.html` | Operations dashboard page |
| `webapp/templates/partials/form_analyze.html` | Analyze form |
| `webapp/templates/partials/form_generate.html` | Generate form |
| `webapp/templates/partials/form_export.html` | Export form |
| `webapp/templates/partials/form_setup.html` | Setup form |
| `webapp/templates/partials/form_check_drift.html` | Check Drift form |
| `webapp/templates/partials/form_feedback.html` | Feedback form |
| `webapp/templates/partials/inline_terminal.html` | Reusable terminal component |
| `webapp/static/operations.js` | WebSocket client + terminal renderer |

### Modified Files

| File | Change |
|------|--------|
| `webapp/app.py` | Include API router, `/operations` route, partials routes |
| `webapp/templates/base.html` | "Operations" nav link, htmx CDN script |
| `webapp/templates/catalog.html` | "Analyze New Product" button, per-row refresh icons |
| `webapp/templates/product.html` | Re-analyze, Regenerate, Check Drift buttons + inline terminal |
| `webapp/static/styles.css` | Terminal, tab, inline form styles |
| `pyproject.toml` | Add `operations.js` to package-data |

### No New Python Dependencies

htmx loaded from CDN (or vendored in `/static`).
