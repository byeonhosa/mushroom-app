# Mushroom App — Claude Code Project Instructions

## Session start (development sessions)
1. `git pull` to sync `main`.
2. Read this file, then `docs/LEAD_DEVELOPER_BRIEF.md`, `docs/ROADMAP.md` and `docs/DECISIONS.md` (if it exists).
3. Continue the first unfinished work package in the roadmap unless the owner's prompt says otherwise.

## Session End (MANDATORY)
1. Commit, push, and merge finished work through a pull request with CI green.
2. Update `docs/ROADMAP.md` and append to `docs/SESSION_LOG.md`.
3. Update the Obsidian vault if the `dryden-vault` repository is attached (see the last section).

## Standing mandate
As of November 11, 2026 the owner has delegated the lead on this app to Claude Code. `docs/LEAD_DEVELOPER_BRIEF.md` sets out the authority, the limits, and the decisions already made. Work autonomously within it.

## Product
Mushroom Farm Manager — production tracking for The Maury River Mushroom Farm, covering the full lifecycle from liquid culture or purchased spawn → spawn → substrate → harvest → disposal. Eventually a read-only data source for the farm's public website (separate repo `byeonhosa/maury-river-mushroom-farm-web`, separate droplet).

- **Repo:** https://github.com/byeonhosa/mushroom-app (currently public; private decision parked). GitHub is the only copy and the source of truth. The owner's laptop was lost in November 2026; no local clone exists.
- **Requirements:** `docs/SRS.md`. **Order of work and current state:** `docs/ROADMAP.md`.
- **Droplet:** 138.197.88.81 (production-app). Online and deploying; its state as of the last deploy is in the deployment table of `docs/ROADMAP.md`.

## Workflow
- Work on a branch, open a pull request, merge by squash when CI is green.
- **GitHub Actions CI is the test gate** (`.github/workflows/ci.yml`): pytest, migration smoke against PostgreSQL, API contract check, dependency audit (`pip-audit`, `npm audit`), frontend typecheck, build, and Playwright e2e. Do not merge on red.
- **Every push to `main` deploys** (`.github/workflows/deploy-droplet.yml`) on the self-hosted runner on the droplet. It pulls, runs `docker compose up -d --build`, waits for the API, and smoke-tests the health endpoint, two API routes and the frontend. Check the result with `gh run list`.
- If a deploy fails at the build, the running containers are unaffected. Fix forward or revert.
- The deploy workflow does **not** run on pull requests. This protects the self-hosted runner on a public repo (forks cannot push to `main`).
- In cloud sessions GitHub's GraphQL API is blocked: `gh pr create` and `gh pr merge` fail. Use the REST calls listed in the brief. The proxy also refuses branch deletion; merged branches are removed by the repository's auto-delete setting once the owner turns it on.

## Tech Stack
- Frontend: Next.js 16.x, React 19 (TypeScript). No Tailwind or UI library; one global `frontend/app/styles.css` with semantic classes. Next.js 16 differs from older versions in APIs and conventions; its documentation ships with the package at `frontend/node_modules/next/dist/docs/`, so check the relevant guide there before using an API you have not used in this codebase. `next-env.d.ts` is generated (`npm run typecheck` runs `next typegen` first) and is not tracked.
- Backend: FastAPI, Python 3.12. Direct dependencies and their ranges are in `backend/requirements.in`; `backend/requirements.txt` and `requirements-dev.txt` are hashed lockfiles compiled from the `.in` files with `pip-compile` (commands at the top of `requirements.in`). The Docker image and CI install from the lockfiles with `--require-hashes`. Never edit a lockfile by hand.
- Database: PostgreSQL 16 (prod), SQLite (dev/test)
- ORM: SQLAlchemy 2.0 — **migrations are raw SQL via `python -m app.migrate` (NOT Alembic)**
- API contract: OpenAPI generated from the code; frontend types generated from it (`npm run generate:api-contract`); CI checks for drift
- Deploy: Docker Compose on one droplet, driven by the self-hosted runner

## Droplet Environment Notes
- **The SSH key was lost with the laptop.** Until the owner installs a new key through the DigitalOcean console, the deploy workflow is the only way to change anything on the droplet. Express server changes as Compose services, Dockerfile changes, or workflow steps.
- The droplet host has **no Python or Node toolchain** — everything runs in containers. Use `docker compose exec api ...` inside workflow steps.
- Repo lives at `/opt/mushroom-app`, owned by the `actions-runner` user, which has Docker access.
- Postgres data persists in the `pgdata` named volume. Never remove it.
- `/opt/mushroom-app/.env` holds `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `APP_ENV`, `CORS_ORIGINS`, `BACKUP_DIR` (set by the deploy workflow) and a leftover `NEXT_PUBLIC_API_BASE` that nothing reads. It exists only on the droplet. Never print it. The deploy workflow changes non-secret keys with `ops/deploy/set-env.sh`.
- As of November 11, 2026 (deploy logs): the runner is online and deploys succeed; all containers run with `restart=unless-stopped`, rotated logs and loopback-only ports; the `backup` service writes daily dumps to `/var/backups/mushroom-app` and every deploy runs a restore test; the database holds no bags. Not verifiable from the workflow: the cloud firewall (blocked 5432, 8000, 3000 in June), sshd (password authentication was re-enabled by a cloud-init drop-in in June), and the reboot that has been pending since June.

## Build & Test Commands

    # Backend
    cd backend && pip install --require-hashes -r requirements.txt -r requirements-dev.txt
    cd backend && pytest -q
    cd backend && uvicorn app.main:app --reload --port 8000
    cd backend && python -m app.seed_demo            # a realistic demo farm in an empty database (docs/OPERATIONS.md 3a)

    # Frontend
    cd frontend && npm ci
    cd frontend && npm run typecheck
    cd frontend && npm run build
    cd frontend && npm run check:api-contract
    cd frontend && npm run test:e2e

Run these in the session before pushing. CI remains the authoritative gate.

## Architecture Notes
- Domain model is bag-centric (SPAWN and SUBSTRATE bag types).
- Bag status is worked out in one place, `_derive_bag_status` in `crud_status.py`, from the immutable event history (`bag_status_events`), with the cached column as the fallback for a bag that has no event of that type.
- `crud.py` is a re-export facade; logic lives in `crud_bags.py`, `crud_dashboard.py`, `crud_reference.py`, `crud_reporting.py`, `crud_status.py`. Add new functions to the appropriate domain module, and add new modules by domain as the code grows.
- One species list: `mushroom_species` holds code, name, the slug shared with the farm website and the website fields; `species_profiles` holds one cultivation profile per species, linked by `species_id`. Both are seeded at container start by `app.seed_species` from `backend/app/seeds/species.json` (the eighteen varieties) and `mushroom_species.json` (the farm's eight source profiles). The seeder only adds; see decision D-030. Species codes and slugs must stay equal to the website's (`docs/research/website-contract-2026-11-11.md`).
- Three inoculation sources (`InoculationSourceType`): a liquid culture, one of the farm's own spawn bags, or a purchased spawn lot (`purchased_spawn_lots`, code `PL-{species}-{YYMMDD}{letter}`). A lot is not a bag: it has no status events and is never consumed; it stays usable until marked used up. Spawn from a lot is generation 1, substrate straight from a lot generation 0 (decisions D-033 to D-038).
- Every time written to a run, a bag or an event comes from `app.clock.now()` (through `_now()` in `crud_status.py` and `farm_today()` in `bag_id.py`). Do not call `datetime.now()` in farm logic. The demo generator `app.seed_demo` replaces that clock and replays twelve weeks of work through the real `crud` functions; it keeps a ledger of its own decisions, and `tests/test_seed_demo.py` checks the reports against it. When a lifecycle rule changes, the generator must still run: it is the widest test of the rules there is. Sign-in keeps real time (`app.auth`).
- **Sign-in exists (WP-2).** Every route but the health checks and `/api/auth/{status,login,logout}` needs a session; `backend/app/auth.py` holds the principal model, the origin check and rate limiting, `api_auth.py` the routes, `manage.py` the server commands (`bootstrap-admin`, `smoke-session`, `reset-password`). New routes go on `router` in `api.py` (signed-in user) and add `dependencies=ADMIN_ONLY` when only an administrator may call them. The path prefix `/api/integration/` is reserved for the website (WP-9). In tests, `client` is a signed-in administrator, `operator_client` an operator and `anon_client` nobody (`backend/tests/conftest.py`).
- The pages call the API on their own origin at `/api` (`frontend/lib/api.ts`); there is no `NEXT_PUBLIC_API_BASE`. In development set `API_PROXY_TARGET` so that `next dev` forwards `/api/*`.
- A run can be corrected after creation (`_correct_run` in `crud_reference.py`), within what already rests on it: recipe, grain and mix lot only before bag records exist, the run code only before a label carries it (decision D-047).
- The dashboard loads all bags and rebuilds the full report on each request: 12.8 s at 10,000 bags. Rework is in WP-6.

## Conventions
- Pydantic v2: `model_config = ConfigDict(from_attributes=True)`, not `class Config`.
- New database changes are new numbered files in `backend/app/migrations/`. Never edit a merged migration.
- Reference data is never deleted. It has an `is_active` flag; a deactivated row stays listed, is filtered out of pick lists by the page, and is refused for new work by `_usable()` in `crud_reference.py` (decision D-043). A new reference list gets its screen from `frontend/lib/reference-list.tsx`.
- Tests accompany every change: pytest through the API, Playwright for screen flows.
- Descriptive commit messages.
- Never commit `.env`, `.env.*`, backups, database volumes, keys or tokens.

## Obsidian Vault Update (end of session, when the vault is attached)

The vault is the Git repo `byeonhosa/dryden-vault`. In a cloud session it is available only if it was attached to the session. If it is not attached, skip this section; `docs/SESSION_LOG.md` in this repository is then the record.

When it is attached, follow the vault's own `CLAUDE.md` for editing rules and commit conventions. The product folder is `10-Products/MushroomApp/` (at the vault repo root, or under `improved-vault/` if that folder exists). Update:

**File 1 — overwrite each time:**
`10-Products/MushroomApp/Current-Context.md`, following `50-Templates/Current-Context-Template.md`.

**File 2 — new file each session (append-only history):**
`10-Products/MushroomApp/Development-Status/MushroomApp_Development_Status_[YYYYMMDD_HHMMSS].md` (Eastern time), with sections: Session Summary (commit, duration), Changes Made, Test Results, Decisions Made, Backlog Items Discovered.

Commit and push the vault with a message of the form `vault: MushroomApp: <what changed and why>`.
