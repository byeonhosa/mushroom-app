# Mushroom App Operations Guide

Status: Draft v1
Last updated: 2026-03-26

## 1. Scope

This guide covers the operational basics for the current mushroom app stack:

- environment setup
- containerized local deployment
- health checks
- backup and restore
- release verification

## 2. Environment Files

Example env files are committed for reproducible setup:

- `.env.example`: compose defaults
- `backend/.env.example`: backend runtime
- `frontend/.env.local.example`: frontend runtime

Recommended setup:

1. Copy `/.env.example` to `/.env`
2. Copy `backend/.env.example` to `backend/.env` if running the backend outside Docker
3. Copy `frontend/.env.local.example` to `frontend/.env.local` if running the frontend outside Docker

## 3. Local Stack

To run the full stack with Docker:

```bash
docker compose up --build
```

Services:

- `db`: PostgreSQL 16
- `api`: FastAPI backend with migrations applied at startup
- `frontend`: Next.js operator UI

Default local URLs:

- frontend: `http://localhost:3000`
- backend API: `http://localhost:8000/api`

## 4. Health Checks

Available backend health endpoints:

- `GET /api/health`: liveness summary
- `GET /api/health/live`: explicit liveness endpoint
- `GET /api/health/ready`: readiness endpoint with DB and migration checks

`/api/health/ready` is the operational endpoint to use for deploy checks because it verifies:

- database connectivity
- presence of `schema_migrations`
- no pending SQL migrations
- presence of the app's required core tables

Expected behavior:

- `200 OK`: app is ready to serve traffic
- `503 Service Unavailable`: DB, migration state, or required tables are not ready

## 5. Backup

The backup helper wraps `pg_dump` and writes a timestamped custom-format dump.

Example:

```bash
cd backend
python scripts/postgres_backup.py --output ../backups/pre_release.dump
```

Default behavior:

- reads `DATABASE_URL` from the environment
- writes dumps under `/backups` when no explicit `--output` path is supplied

Prerequisite:

- PostgreSQL client tools must be installed locally so `pg_dump` is available on `PATH`

## 6. Restore

The restore helper wraps `dropdb`, `createdb`, and `pg_restore`.

Example:

```bash
cd backend
python scripts/postgres_restore.py --input ../backups/pre_release.dump
```

Default behavior:

- reads `DATABASE_URL` from the environment
- drops and recreates the target database before restoring

Optional flag:

- `--skip-drop-create`: restore into an existing database without recreating it first

Prerequisite:

- PostgreSQL client tools must be installed locally so `dropdb`, `createdb`, and `pg_restore` are available on `PATH`

## 7. Release Checklist

Before a production or farm-floor deployment:

1. Run `pytest -q`
2. Run `npm run typecheck` in `frontend/`
3. Run `npm run build` in `frontend/`
4. Run `npm run check:api-contract` in `frontend/`
5. Run `npm run test:e2e` in `frontend/`
6. Take a backup before applying a production upgrade
7. Confirm `GET /api/health/ready` returns `200`

## 8. Recovery Notes

If a deployment goes wrong:

1. Stop new writes to the app
2. Restore the most recent known-good backup into PostgreSQL
3. Start the API and confirm `GET /api/health/ready` is green
4. Open the dashboard and check alerts, queues, and recent activity
5. Review contamination and reporting pages if any data repair is suspected
