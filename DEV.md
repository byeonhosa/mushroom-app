# Mushroom App — Dev Guide

## Prereqs
- Docker + Docker Compose plugin
- Python 3.12 + venv
- Node 22 + npm

## Repo layout
- backend/ (FastAPI + SQLAlchemy)
- frontend/ (Next.js)
- docker-compose.yml (Postgres)

## First-time setup (backend)
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
# runtime deps (if requirements.txt exists and is populated)
pip install -r requirements.txt
# dev/test deps
pip install -r requirements-dev.txt
