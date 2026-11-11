# Mushroom App Operations Guide

Status: Draft v1, backup and restore sections rewritten November 2026 (WP-1). A full rewrite for the server as it now runs is planned in WP-7.
Last updated: 2026-11-11

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
- `backup`: daily database dumps (section 5)
- `proxy`: Caddy, the one way in from outside (section 6a)

Every service has `restart: unless-stopped`, so the stack comes back by itself after a crash or a reboot. The database, the API and the frontend are published on `127.0.0.1` only; the proxy publishes 80 and 443. Container logs rotate at 10 MB, five files each.

Default local URLs:

- the app, through the proxy: `http://localhost`
- frontend directly: `http://localhost:3000`
- backend API directly: `http://localhost:8000/api`

To sign in to a local stack, set `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` in `.env` before the first start.

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

The `backup` Compose service (`ops/backup/`) is built from the same `postgres:16` image as the database, so `pg_dump` always matches the server. It needs nothing installed on the host.

What it does:

- Writes a custom-format dump (`pg_dump -Fc`) once every 24 hours into `daily/`, and keeps the newest 14.
- Checks every dump with `pg_restore --list` before keeping it. A dump that fails is discarded and the container exits non-zero, so Docker restarts it and the failure shows in `docker compose ps`.
- The deploy workflow takes one more dump into `predeploy/` before each deploy, before any migration runs, and keeps the newest 5.

Where the dumps are: the host directory named by `BACKUP_DIR` in `.env`. On the droplet that is `/var/backups/mushroom-app`, outside the repository checkout. Locally it defaults to `./backups`. Files are readable by root only.

These copies are on the same server as the database. A copy off the server is the DigitalOcean droplet backup, which the owner switches on (roadmap, owner action O5).

Commands, run from the repository directory on the server:

```bash
docker compose exec backup backup status          # what is on disk, and how old the newest daily dump is
docker compose exec backup backup once            # a daily dump now
docker compose exec backup backup once predeploy  # a pre-deploy dump now
docker compose exec backup backup verify          # restore test, see below
```

Every deploy runs `status` and `verify` and prints the result in the workflow log.

## 6. Restore

**Restore test (safe, run on every deploy and in CI).** `backup verify` restores the newest dump into a scratch database named `<database>_restore_check`, counts the rows in every table, compares them with the live database, and drops the scratch database. It never touches the live database.

**Real restore (replaces the live database).** Stop the API first so that nothing writes during the restore, then restore, then start it again:

```bash
docker compose stop api frontend
docker compose exec -e RESTORE_CONFIRM=mushroom backup backup restore daily/mushroom_YYYYMMDD_HHMMSS.dump
docker compose up -d
```

`RESTORE_CONFIRM` must equal the database name (`POSTGRES_DB`); without it the command refuses. A safety dump of the current state is written to `predeploy/` before anything is replaced.

## 6a. Sign-in, users and the way in

**The way in.** The `proxy` service (Caddy, `ops/proxy/`) is the only service published beyond the server itself, on ports 80 and 443. It sends `/api/*` to the API and everything else to the frontend. When the repository variable `APP_HOSTNAME` is set it serves HTTPS with a certificate it obtains and renews by itself, and sends plain HTTP on to HTTPS. Certificates live in the `caddy_data` volume.

**The first administrator.** Created by the deploy workflow from the repository secrets `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`, once, when no user exists. After that the secrets are not used again and can be deleted.

**Adding and removing people.** An administrator does this in the app, on the **Users** screen. Nobody is deleted: a person who leaves is deactivated, which signs them out at once and keeps their name on the events they entered.

**A forgotten password.** Another administrator resets it on the Users screen. If the only administrator is locked out, from the server (DigitalOcean console > the droplet > Access > Launch Droplet Console):

```bash
cd /opt/mushroom-app
docker compose run --rm --no-deps -e NEW_PASSWORD='a new password of 10+ characters' \
  api python -m app.manage reset-password --email you@example.com
```

The account is signed out everywhere and must choose a new password at next sign-in.

**Who can do what.** An operator records runs, bags, inoculations, events and harvests, and reads the reports. An administrator can also maintain species, grain types, fill profiles and ingredients, and manage users.

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
