# Mushroom App — Claude Code Project Instructions

## Session Start (MANDATORY)
1. `git pull` to sync any changes pushed from the droplet or other sessions.
2. Read this file.

## Session End (MANDATORY)
1. Commit with a descriptive message and `git push`.
2. Update the Obsidian vault (see Obsidian section below).

## Product
Mushroom Farm Manager — production tracking for The Maury River Mushroom Farm, covering the full lifecycle from liquid culture → spawn → substrate → harvest → disposal.

- **Repo:** https://github.com/byeonhosa/mushroom-app (public)
- **Droplet:** 138.197.88.81
- **Vault context:** C:\Knowledge\dryden-vault\improved-vault\10-Products\MushroomApp\Current-Context.md

## Workflow
- Claude Code creates/edits files, commits, and pushes directly to main.
- John pulls on the droplet and tests there. Do NOT run servers, tests, or database commands locally.
- Deployment: password authentication (not SSH keys). NEXT_PUBLIC_API_BASE must be set to droplet public IP before build.

## Tech Stack
- Frontend: Next.js (TypeScript)
- Backend: FastAPI (Python 3.12)
- Database: PostgreSQL (prod), SQLite (dev/test)
- ORM: SQLAlchemy + Alembic
- API contract: OpenAPI spec auto-generated, frontend types generated from it
- CI: GitHub Actions

## Build & Test Commands (for reference — run on droplet, not locally)

    # Backend
    cd backend && pytest -q
    cd backend && uvicorn app.main:app --reload --port 8000

    # Frontend
    cd frontend && npm run dev
    cd frontend && npm run typecheck
    cd frontend && npm run build

## Architecture Notes
- Domain model is bag-centric (SPAWN and SUBSTRATE bag types)
- Bag status derives from immutable event history first, with cache-based fallback
- No authentication exists yet — API is completely open
- Dashboard loads ALL bags unbounded — will need pagination at scale

## Known Tech Debt
- crud.py is 2,093 lines — planned split into crud_bags, crud_reporting, crud_dashboard, crud_reference, crud_status
- 15 Pydantic v2 deprecation instances resolved; watch for regressions

## Conventions
- Run pytest -q and npm run typecheck before committing.
- Pydantic v2: use model_config = ConfigDict(from_attributes=True), not deprecated class Config.
- Commit messages should be descriptive.
- Always check that tests pass after changes to crud.py or schemas.py.

## Obsidian Vault Update (MANDATORY — end of every session)

File 1 — overwrite each time:
C:\Knowledge\dryden-vault\improved-vault\10-Products\MushroomApp\Current-Context.md

Sections: Last updated, Last commit, What Works Right Now, What Was Done This Session, Known Issues / Tech Debt, Next Up, Architecture Notes, Environment Setup.

File 2 — new file each session:
C:\Knowledge\dryden-vault\improved-vault\10-Products\MushroomApp\Development-Status\MushroomApp_Development_Status_[YYYYMMDD_HHMMSS].md

Sections: Session Summary (commit, duration), Changes Made, Test Results, Decisions Made, Backlog Items Discovered.

Create the Development-Status directory if it doesn't exist.
