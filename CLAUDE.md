# Mushroom App — Claude Code Project Instructions

## Session Start (MANDATORY)
1. `git pull` to sync any changes pushed from the droplet or other sessions.
2. Read this file.

## Session End (MANDATORY)
1. Commit with a descriptive message and `git push`.
2. Update the Obsidian vault (see Obsidian section below).

## Product
Mushroom Farm Manager — production tracking for The Maury River Mushroom Farm, covering the full lifecycle from liquid culture → spawn → substrate → harvest → disposal. Eventually a read-only data source for The Maury River Mushroom Farm public website (separate repo, separate droplet).

- **Repo:** https://github.com/byeonhosa/mushroom-app (currently public; private decision parked)
- **Droplet:** 138.197.88.81 (production-app)
- **Vault context:** C:\Knowledge\dryden-vault\improved-vault\10-Products\MushroomApp\Current-Context.md

## Workflow
- Claude Code creates/edits files, commits, and pushes (typically via PR; can push directly to main for trivial changes).
- **GitHub Actions CI is the test gate** (`.github/workflows/ci.yml`): pytest, migration smoke against PostgreSQL, API contract check, frontend typecheck, build, and Playwright e2e. PRs should not be merged unless CI is green.
- **On every push to `main`, the deploy workflow runs automatically** (`.github/workflows/deploy-droplet.yml`) on the self-hosted runner on the droplet. It pulls, runs `docker compose up -d --build`, waits for the API to respond, and smoke-tests `/api/health/ready`, `/api/species`, `/api/dashboard/overview`, and the frontend. Watch the result in the GitHub Actions UI.
- If a deploy fails, the running containers are unaffected — Docker keeps the previous image until a successful build replaces it. Fix forward by pushing a corrective commit to main.
- The deploy workflow does **not** trigger on PR pushes — only on push to main. This is intentional security for the self-hosted runner on a public repo (forks cannot push to main).

## Tech Stack
- Frontend: Next.js 16.x (TypeScript)
- Backend: FastAPI 0.115.x (Python 3.12)
- Database: PostgreSQL 16 (prod), SQLite (dev/test)
- ORM: SQLAlchemy 2.0 — **migrations are raw SQL via `python -m app.migrate` (NOT Alembic)**
- API contract: OpenAPI spec auto-generated; frontend types generated from it; CI checks for drift
- CI: GitHub Actions (`.github/workflows/ci.yml`)
- Deploy: GitHub Actions self-hosted runner on droplet (`.github/workflows/deploy-droplet.yml`)

## Droplet Environment Notes
- The droplet host has **no Python or Node toolchain** — everything runs in Docker containers. Do not assume `pytest` or `npm` is available on the droplet host. Use `docker compose exec api ...` if you need to run a command inside a container.
- Repo lives at `/opt/mushroom-app` on the droplet, owned by the `actions-runner` user.
- Postgres data persists in the `pgdata` named volume across rebuilds.
- A DigitalOcean Cloud Firewall blocks public access to ports 5432 (Postgres), 8000 (API), 3000 (frontend). SSH (22) is open to all IPs but uses key-only auth.
- SSH config alias on the laptop: `ssh mushroom-app` (uses `~/.ssh/id_ed25519`).

## Build & Test Commands (reference — for local development only)

    # Backend
    cd backend && pytest -q
    cd backend && uvicorn app.main:app --reload --port 8000

    # Frontend
    cd frontend && npm run dev
    cd frontend && npm run typecheck
    cd frontend && npm run build

These are for ad-hoc local testing if you have the toolchain. The droplet does not — CI is the authoritative test gate.

## Architecture Notes
- Domain model is bag-centric (SPAWN and SUBSTRATE bag types).
- Bag status derives from immutable event history first, with cache-based fallback (note: the two derivation paths have different defaults — see audit §4.3 for drift risk).
- `crud.py` is now an 88-line re-export facade; actual logic lives in `crud_bags.py`, `crud_dashboard.py`, `crud_reference.py`, `crud_reporting.py`, `crud_status.py`. Add new functions to the appropriate domain module.
- **No authentication exists yet** — API is open at the application layer, network-protected by the droplet firewall. Operator + integration auth is the next major batch of work.
- Dashboard loads ALL bags unbounded and `get_dashboard_overview` calls `get_production_report` which reloads the same set — known performance issue, will need pagination + reuse-bags optimization at scale.

## Known Tech Debt (high-priority items only — full list in audit doc)
- No application-layer auth → next batch of work (expanded Batch 1: integration + operator auth).
- Dependency CVEs: `fastapi==0.115.6`, `uvicorn==0.30.6`, `next ^16.1.6`, unpinned Pillow → bump as part of next batch.
- Status derivation drift between cache-based and history-based paths.
- `harvest_events.flush_number CHECK (1, 2)` — hard cap at 2 flushes.
- Stale frontend routes: `frontend/app/{blocks,batches,spawn-batches}/` from bag-centric rebuild.
- Backup script likely writes inside container (no `backups:` volume) — confirm persistence on droplet.

## Conventions
- Pydantic v2: use `model_config = ConfigDict(from_attributes=True)`, not deprecated `class Config`.
- Commit messages should be descriptive.
- Run `pytest -q` and `npm run typecheck` locally before committing if your environment supports it; otherwise rely on CI.
- Never commit `.env`, `.env.*`, backups, database volumes, or SSH keys (gitignored, but be careful).

## Obsidian Vault Update (MANDATORY — end of every session)

The vault is itself a Git repo (`https://github.com/byeonhosa/dryden-vault`).
For the editing rules, structure overview, and commit-and-push workflow, see
the vault's own CLAUDE.md at
`C:\Knowledge\dryden-vault\improved-vault\CLAUDE.md` — it is the source of
truth. This section names only the MushroomApp-specific files to touch.

**File 1 — overwrite each time:**
`C:\Knowledge\dryden-vault\improved-vault\10-Products\MushroomApp\Current-Context.md`

Follow the canonical template at
`C:\Knowledge\dryden-vault\improved-vault\50-Templates\Current-Context-Template.md`.
The template is the source of truth — do not enumerate sections here, because
that's what created drift in the first place. Required vs. optional sections
are marked inside the template.

**File 2 — new file each session (append-only history):**
`C:\Knowledge\dryden-vault\improved-vault\10-Products\MushroomApp\Development-Status\MushroomApp_Development_Status_[YYYYMMDD_HHMMSS].md`

Sections: Session Summary (commit, duration), Changes Made, Test Results,
Decisions Made, Backlog Items Discovered.

Create the Development-Status directory if it doesn't exist.

**Commit + push the vault changes** with a message of the form
`vault: MushroomApp: <what changed and why>` (per the convention in the
vault's CLAUDE.md). Direct edits without commit-and-push create drift — the
hourly Pi auto-backup cron is a safety net, not the workflow.
