# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

## Project Overview

Self-hosted browser profile manager (multilogin/gologin alternative). Each profile is an isolated local CloakBrowser instance with unique fingerprint, proxy, cookies, and session data.

## Architecture

- **Backend**: FastAPI (`backend/main.py`) serves REST API + static React build
- **Frontend**: React + Vite + Tailwind (`frontend/`)
- **Database**: SQLite (`DATA_DIR/profiles.db`) with WAL mode, defaulting to `~/.cloakbrowser-manager`
- **Browser engine**: CloakBrowser binary (Chromium fork) — launched per profile via Playwright
- **CDP access**: Chrome DevTools Protocol proxied for external automation (Playwright/Puppeteer)

## Dev Commands

### Backend (Python)

```bash
cd CloakBrowser-Manager
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8080
```

### Frontend (TypeScript)

```bash
cd frontend
npm install
npm run dev       # Vite dev server
npm run build     # Production build → frontend/dist/
npm run test      # Vitest (jsdom)
npm run test:watch
```

### Tests

```bash
# Backend — from repo root, pytest configured in pyproject.toml
pytest backend/tests/

# Frontend
cd frontend && npm test
```

- Backend tests mock `cloakbrowser` at module level in `conftest.py` — no real browser needed
- `pyproject.toml` sets `testpaths = ["backend/tests"]`

### Docker

```bash
docker compose up --build   # Full stack at http://localhost:8080
```

## Key Gotchas

- **No `cloakbrowser` binary in tests** — tests mock it. Real browser launch requires running the backend on a host with a desktop session.
- **Database path** defaults to `~/.cloakbrowser-manager/profiles.db`. Override `DATA_DIR` in runtime or `DB_PATH` / `DATA_DIR` via monkeypatch in tests.
- **Auth middleware** is raw ASGI (`AuthMiddleware`), not `BaseHTTPMiddleware` — the latter breaks WebSocket routes.
- **CDP ports** cycle through 5100–5199 to avoid TIME_WAIT collisions.
- **`cloakbrowser` package** is imported at module level in `browser_manager.py` — if it's not installed, the whole backend fails to import.
- **Frontend SPA** catch-all route is registered AFTER all `/api/` routes in `main.py`. Never add static mount before API routes.

## File Layout

```
backend/
  main.py              # FastAPI app, auth, CDP proxies, SPA serving
  browser_manager.py   # Launch/stop CloakBrowser instances
  database.py          # SQLite CRUD, migrations
  models.py            # Pydantic request/response models
  tests/               # pytest, mocks cloakbrowser at import time

frontend/
  src/App.tsx          # Main SPA, auth state machine
  src/components/      # React UI components
  src/hooks/           # React hooks (useProfiles, etc.)
  src/lib/             # API client, utilities
```

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **CloakBrowser-Manager** (1022 symbols, 2092 relationships, 43 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/CloakBrowser-Manager/context` | Codebase overview, check index freshness |
| `gitnexus://repo/CloakBrowser-Manager/clusters` | All functional areas |
| `gitnexus://repo/CloakBrowser-Manager/processes` | All execution flows |
| `gitnexus://repo/CloakBrowser-Manager/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
