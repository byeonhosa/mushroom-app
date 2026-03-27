# Mushroom App Dev Guide

## Prereqs

- Docker + Docker Compose plugin
- Python 3.12 + venv
- Node 22 + npm

## Repo Layout

- `backend/`: FastAPI + SQLAlchemy
- `frontend/`: Next.js
- `docker-compose.yml`: full local stack
- `docs/OPERATIONS.md`: deployment, health, backup, and restore guide

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

If you are running the backend outside Docker, copy `backend/.env.example` to `backend/.env` first.

## Frontend Setup

```bash
cd frontend
npm ci
```

If you are running the frontend outside Docker, copy `frontend/.env.local.example` to `frontend/.env.local` first.

## Local Development

Run the full stack with Docker:

```bash
docker compose up --build
```

Run services individually:

```bash
cd backend
python -m app.migrate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm run dev
```

## Verification Commands

Backend:

```bash
cd backend
pytest -q
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
npm run check:api-contract
npm run test:e2e
```

## Operational Notes

Use `docs/OPERATIONS.md` for:

- readiness checks
- backup and restore
- release checklist
- recovery steps
