#!/usr/bin/env bash
set -euo pipefail

ROOT="$HOME/projects/mushroom-app"
cd "$ROOT"

# Root files
cat > docker-compose.yml <<'YAML'
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: mushroom
      POSTGRES_PASSWORD: mushroom
      POSTGRES_DB: mushroom
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
YAML

cat > .env.example <<'ENV'
DATABASE_URL=postgresql+psycopg://mushroom:mushroom@localhost:5432/mushroom
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
ENV

cat > .gitignore <<'GIT'
# OS / editor
.DS_Store
Thumbs.db
.vscode/
.idea/

# Env / secrets
.env
.env.*
**/.env
**/.env.*

# Python
__pycache__/
*.pyc
.venv/
venv/

# Node / Next
node_modules/
.next/
out/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Docker / local data
pgdata/
GIT

# Backend requirements
cat > backend/requirements.txt <<'REQ'
fastapi==0.115.6
uvicorn[standard]==0.30.6
SQLAlchemy==2.0.32
psycopg[binary]==3.2.1
pydantic==2.8.2
pydantic-settings==2.4.0
python-dateutil==2.9.0.post0
REQ

# Backend app files
cat > backend/app/config.py <<'PY'
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"

settings = Settings()
PY

cat > backend/app/db.py <<'PY'
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
PY

cat > backend/app/models.py <<'PY'
import enum
from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Numeric, Text, Enum, CheckConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class ZoneType(str, enum.Enum):
    INCUBATION = "INCUBATION"
    FRUITING = "FRUITING"
    MIXING = "MIXING"
    OTHER = "OTHER"

class SpawnSourceType(str, enum.Enum):
    PURCHASED = "PURCHASED"
    IN_HOUSE = "IN_HOUSE"

class ThermalProcessType(str, enum.Enum):
    PASTEURIZATION_STEAM = "PASTEURIZATION_STEAM"
    STERILIZATION_AUTOCLAVE = "STERILIZATION_AUTOCLAVE"

class Zone(Base):
    __tablename__ = "zones"
    zone_id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    zone_type = Column(Enum(ZoneType), nullable=False, default=ZoneType.OTHER)

class FillProfile(Base):
    __tablename__ = "fill_profiles"
    fill_profile_id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    target_dry_kg_per_bag = Column(Numeric(10, 3), nullable=False)
    target_water_kg_per_bag = Column(Numeric(10, 3), nullable=False)
    notes = Column(Text)

class SubstrateRecipeVersion(Base):
    __tablename__ = "substrate_recipe_versions"
    substrate_recipe_version_id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)

class ThermalRun(Base):
    __tablename__ = "thermal_runs"
    thermal_run_id = Column(Integer, primary_key=True)
    process_type = Column(Enum(ThermalProcessType), nullable=False)
    unloaded_at = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text)

class SpawnBatch(Base):
    __tablename__ = "spawn_batches"
    spawn_batch_id = Column(Integer, primary_key=True)
    source_type = Column(Enum(SpawnSourceType), nullable=False)
    name = Column(String(120), nullable=False)
    vendor_lot_code = Column(String(120), nullable=True)
    notes = Column(Text)

class SubstrateBatch(Base):
    __tablename__ = "substrate_batches"
    substrate_batch_id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    substrate_recipe_version_id = Column(Integer, ForeignKey("substrate_recipe_versions.substrate_recipe_version_id"), nullable=False)
    fill_profile_id = Column(Integer, ForeignKey("fill_profiles.fill_profile_id"), nullable=False)
    bag_count = Column(Integer, nullable=False)

    mixed_at = Column(DateTime(timezone=True), server_default=func.now())
    mix_zone_id = Column(Integer, ForeignKey("zones.zone_id"), nullable=True)

    incubation_zone_id = Column(Integer, ForeignKey("zones.zone_id"), nullable=True)
    incubation_start_at = Column(DateTime(timezone=True), nullable=True)
    fruiting_zone_id = Column(Integer, ForeignKey("zones.zone_id"), nullable=True)

    thermal_run_id = Column(Integer, ForeignKey("thermal_runs.thermal_run_id"), nullable=True)

    sample_moisture_wb_pct = Column(Numeric(6, 3), nullable=True)
    sample_wet_weight_kg = Column(Numeric(10, 3), nullable=True)

    notes = Column(Text)

    recipe = relationship("SubstrateRecipeVersion")
    fill_profile = relationship("FillProfile")
    inoculations = relationship("BatchInoculation", back_populates="substrate_batch")
    bags = relationship("SubstrateBag", back_populates="batch", cascade="all, delete-orphan")

class BatchInoculation(Base):
    __tablename__ = "batch_inoculations"
    batch_inoculation_id = Column(Integer, primary_key=True)
    substrate_batch_id = Column(Integer, ForeignKey("substrate_batches.substrate_batch_id"), nullable=False)
    spawn_batch_id = Column(Integer, ForeignKey("spawn_batches.spawn_batch_id"), nullable=False)
    inoculated_at = Column(DateTime(timezone=True), server_default=func.now())
    spawn_units_count = Column(Integer, nullable=True)
    spawn_used_qty_kg = Column(Numeric(10, 3), nullable=True)
    notes = Column(Text)

    spawn_batch = relationship("SpawnBatch")
    substrate_batch = relationship("SubstrateBatch", back_populates="inoculations")

class SubstrateBag(Base):
    __tablename__ = "substrate_bags"
    bag_id = Column(String(64), primary_key=True)
    substrate_batch_id = Column(Integer, ForeignKey("substrate_batches.substrate_batch_id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(40), nullable=False, default="INCUBATING")

    batch = relationship("SubstrateBatch", back_populates="bags")
    harvest_events = relationship("HarvestEvent", back_populates="bag", cascade="all, delete-orphan")

class HarvestEvent(Base):
    __tablename__ = "harvest_events"
    harvest_event_id = Column(Integer, primary_key=True)
    bag_id = Column(String(64), ForeignKey("substrate_bags.bag_id"), nullable=False)
    harvested_at = Column(DateTime(timezone=True), server_default=func.now())
    flush_number = Column(Integer, nullable=False)
    fresh_weight_kg = Column(Numeric(10, 3), nullable=False)
    notes = Column(Text)

    __table_args__ = (
        CheckConstraint("flush_number IN (1,2)", name="ck_flush_number_1_2"),
    )

    bag = relationship("SubstrateBag", back_populates="harvest_events")
PY

cat > backend/app/schemas.py <<'PY'
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class FillProfileCreate(BaseModel):
    name: str
    target_dry_kg_per_bag: float
    target_water_kg_per_bag: float
    notes: Optional[str] = None

class FillProfileOut(FillProfileCreate):
    fill_profile_id: int
    class Config: from_attributes = True

class SubstrateBatchCreate(BaseModel):
    name: str = Field(..., description="Human label, used as bag ID prefix")
    substrate_recipe_version_id: int
    fill_profile_id: int
    bag_count: int
    mixed_at: Optional[datetime] = None
    mix_zone_id: Optional[int] = None
    incubation_zone_id: Optional[int] = None
    incubation_start_at: Optional[datetime] = None
    fruiting_zone_id: Optional[int] = None
    thermal_run_id: Optional[int] = None
    sample_moisture_wb_pct: Optional[float] = None
    sample_wet_weight_kg: Optional[float] = None
    notes: Optional[str] = None

class SubstrateBatchOut(SubstrateBatchCreate):
    substrate_batch_id: int
    class Config: from_attributes = True

class SubstrateBagOut(BaseModel):
    bag_id: str
    substrate_batch_id: int
    created_at: datetime
    status: str
    class Config: from_attributes = True

class HarvestEventCreate(BaseModel):
    bag_id: str
    flush_number: int
    fresh_weight_kg: float
    harvested_at: Optional[datetime] = None
    notes: Optional[str] = None

class HarvestEventOut(HarvestEventCreate):
    harvest_event_id: int
    class Config: from_attributes = True

class BagDetailOut(SubstrateBagOut):
    harvest_events: List[HarvestEventOut] = []

class BatchMetricsOut(BaseModel):
    substrate_batch_id: int
    total_harvest_kg: float
    dry_kg_total: float
    be_percent: float
PY

cat > backend/app/crud.py <<'PY'
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from . import models

def create_fill_profile(db: Session, name: str, dry: float, water: float, notes: str | None):
    fp = models.FillProfile(name=name, target_dry_kg_per_bag=dry, target_water_kg_per_bag=water, notes=notes)
    db.add(fp); db.commit(); db.refresh(fp)
    return fp

def list_fill_profiles(db: Session):
    return db.execute(select(models.FillProfile).order_by(models.FillProfile.fill_profile_id)).scalars().all()

def create_substrate_batch(db: Session, data: dict):
    batch = models.SubstrateBatch(**data)
    db.add(batch)
    db.commit()
    db.refresh(batch)

    for i in range(1, batch.bag_count + 1):
        bag_id = f"{batch.name}-{i:04d}"
        db.add(models.SubstrateBag(bag_id=bag_id, substrate_batch_id=batch.substrate_batch_id))
    db.commit()
    return db.get(models.SubstrateBatch, batch.substrate_batch_id)

def list_batches(db: Session):
    return db.execute(select(models.SubstrateBatch).order_by(models.SubstrateBatch.substrate_batch_id.desc())).scalars().all()

def get_bags_for_batch(db: Session, substrate_batch_id: int):
    return db.execute(
        select(models.SubstrateBag).where(models.SubstrateBag.substrate_batch_id == substrate_batch_id).order_by(models.SubstrateBag.bag_id)
    ).scalars().all()

def get_bag_detail(db: Session, bag_id: str):
    bag = db.get(models.SubstrateBag, bag_id)
    if not bag:
        return None
    _ = bag.harvest_events
    return bag

def create_harvest_event(db: Session, data: dict):
    ev = models.HarvestEvent(**data)
    db.add(ev); db.commit(); db.refresh(ev)
    return ev

def batch_metrics(db: Session, substrate_batch_id: int):
    batch = db.get(models.SubstrateBatch, substrate_batch_id)
    if not batch:
        return None

    total_harvest = db.execute(
        select(func.coalesce(func.sum(models.HarvestEvent.fresh_weight_kg), 0))
        .join(models.SubstrateBag, models.SubstrateBag.bag_id == models.HarvestEvent.bag_id)
        .where(models.SubstrateBag.substrate_batch_id == substrate_batch_id)
    ).scalar_one()

    dry_per_bag = float(batch.fill_profile.target_dry_kg_per_bag)
    dry_total = dry_per_bag * batch.bag_count
    be = (float(total_harvest) / dry_total * 100.0) if dry_total > 0 else 0.0

    return {
        "substrate_batch_id": substrate_batch_id,
        "total_harvest_kg": float(total_harvest),
        "dry_kg_total": float(dry_total),
        "be_percent": float(be),
    }
PY

cat > backend/app/api.py <<'PY'
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .db import get_db
from . import schemas, crud

router = APIRouter()

@router.get("/health")
def health():
    return {"ok": True}

@router.get("/fill-profiles", response_model=list[schemas.FillProfileOut])
def fill_profiles(db: Session = Depends(get_db)):
    return crud.list_fill_profiles(db)

@router.post("/fill-profiles", response_model=schemas.FillProfileOut)
def create_fill_profile(payload: schemas.FillProfileCreate, db: Session = Depends(get_db)):
    return crud.create_fill_profile(db, payload.name, payload.target_dry_kg_per_bag, payload.target_water_kg_per_bag, payload.notes)

@router.get("/batches", response_model=list[schemas.SubstrateBatchOut])
def list_batches(db: Session = Depends(get_db)):
    return crud.list_batches(db)

@router.post("/batches", response_model=schemas.SubstrateBatchOut)
def create_batch(payload: schemas.SubstrateBatchCreate, db: Session = Depends(get_db)):
    return crud.create_substrate_batch(db, payload.model_dump(exclude_unset=True))

@router.get("/batches/{batch_id}/bags", response_model=list[schemas.SubstrateBagOut])
def list_batch_bags(batch_id: int, db: Session = Depends(get_db)):
    return crud.get_bags_for_batch(db, batch_id)

@router.get("/batches/{batch_id}/metrics", response_model=schemas.BatchMetricsOut)
def get_batch_metrics(batch_id: int, db: Session = Depends(get_db)):
    m = crud.batch_metrics(db, batch_id)
    if not m:
        raise HTTPException(404, "Batch not found")
    return m

@router.get("/bags/{bag_id}", response_model=schemas.BagDetailOut)
def bag_detail(bag_id: str, db: Session = Depends(get_db)):
    bag = crud.get_bag_detail(db, bag_id)
    if not bag:
        raise HTTPException(404, "Bag not found")
    return bag

@router.post("/harvest-events", response_model=schemas.HarvestEventOut)
def create_harvest(payload: schemas.HarvestEventCreate, db: Session = Depends(get_db)):
    return crud.create_harvest_event(db, payload.model_dump(exclude_unset=True))
PY

cat > backend/app/main.py <<'PY'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .api import router

app = FastAPI(title="Mushroom Farm App API", version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
PY

cat > backend/app/migrations/001_init.sql <<'SQL'
CREATE TABLE IF NOT EXISTS zones (
  zone_id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  zone_type VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS fill_profiles (
  fill_profile_id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  target_dry_kg_per_bag NUMERIC(10,3) NOT NULL,
  target_water_kg_per_bag NUMERIC(10,3) NOT NULL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS substrate_recipe_versions (
  substrate_recipe_version_id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS thermal_runs (
  thermal_run_id SERIAL PRIMARY KEY,
  process_type VARCHAR(40) NOT NULL,
  unloaded_at TIMESTAMPTZ NOT NULL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS spawn_batches (
  spawn_batch_id SERIAL PRIMARY KEY,
  source_type VARCHAR(20) NOT NULL,
  name VARCHAR(120) NOT NULL,
  vendor_lot_code VARCHAR(120),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS substrate_batches (
  substrate_batch_id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  substrate_recipe_version_id INT NOT NULL REFERENCES substrate_recipe_versions(substrate_recipe_version_id),
  fill_profile_id INT NOT NULL REFERENCES fill_profiles(fill_profile_id),
  bag_count INT NOT NULL,
  mixed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  mix_zone_id INT REFERENCES zones(zone_id),
  incubation_zone_id INT REFERENCES zones(zone_id),
  incubation_start_at TIMESTAMPTZ,
  fruiting_zone_id INT REFERENCES zones(zone_id),
  thermal_run_id INT REFERENCES thermal_runs(thermal_run_id),
  sample_moisture_wb_pct NUMERIC(6,3),
  sample_wet_weight_kg NUMERIC(10,3),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS substrate_bags (
  bag_id VARCHAR(64) PRIMARY KEY,
  substrate_batch_id INT NOT NULL REFERENCES substrate_batches(substrate_batch_id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  status VARCHAR(40) NOT NULL DEFAULT 'INCUBATING'
);

CREATE TABLE IF NOT EXISTS batch_inoculations (
  batch_inoculation_id SERIAL PRIMARY KEY,
  substrate_batch_id INT NOT NULL REFERENCES substrate_batches(substrate_batch_id) ON DELETE CASCADE,
  spawn_batch_id INT NOT NULL REFERENCES spawn_batches(spawn_batch_id),
  inoculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  spawn_units_count INT,
  spawn_used_qty_kg NUMERIC(10,3),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS harvest_events (
  harvest_event_id SERIAL PRIMARY KEY,
  bag_id VARCHAR(64) NOT NULL REFERENCES substrate_bags(bag_id) ON DELETE CASCADE,
  harvested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  flush_number INT NOT NULL,
  fresh_weight_kg NUMERIC(10,3) NOT NULL,
  notes TEXT,
  CONSTRAINT ck_flush_number_1_2 CHECK (flush_number IN (1,2))
);
SQL

cat > backend/app/migrations/002_seed_defaults.sql <<'SQL'
INSERT INTO zones(name, zone_type)
VALUES
  ('Mixing Area', 'MIXING'),
  ('Incubation Tent 1', 'INCUBATION'),
  ('Fruiting Tent 1', 'FRUITING')
ON CONFLICT DO NOTHING;

INSERT INTO fill_profiles(name, target_dry_kg_per_bag, target_water_kg_per_bag, notes)
VALUES ('Standard 1.00kg dry + 1.25kg water', 1.000, 1.250, 'Current hand-fill standard')
ON CONFLICT DO NOTHING;

INSERT INTO substrate_recipe_versions(name, notes)
VALUES ('Default Substrate Recipe v1', 'Set items in Phase 3 once ingredient lots are tracked')
ON CONFLICT DO NOTHING;
SQL

cat > backend/app/migrate.py <<'PY'
from pathlib import Path
from sqlalchemy import create_engine, text
from .config import settings

MIG_DIR = Path(__file__).parent / "migrations"

def ensure_schema_migrations(engine):
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
          id SERIAL PRIMARY KEY,
          filename TEXT NOT NULL UNIQUE,
          applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """))

def applied(engine) -> set[str]:
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT filename FROM schema_migrations")).fetchall()
        return {r[0] for r in rows}

def apply_migration(engine, filename: str, sql: str):
    with engine.begin() as conn:
        conn.execute(text(sql))
        conn.execute(text("INSERT INTO schema_migrations(filename) VALUES (:f)"), {"f": filename})

def main():
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    ensure_schema_migrations(engine)
    done = applied(engine)

    files = sorted([p for p in MIG_DIR.glob("*.sql")])
    for p in files:
        if p.name in done:
            continue
        sql = p.read_text(encoding="utf-8")
        apply_migration(engine, p.name, sql)
        print(f"Applied {p.name}")

if __name__ == "__main__":
    main()
PY

# Frontend minimal files
cat > frontend/package.json <<'JSON'
{
  "name": "mushroom-frontend",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000"
  },
  "dependencies": {
    "next": "14.2.5",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  }
}
JSON

cat > frontend/next.config.js <<'JS'
/** @type {import('next').NextConfig} */
const nextConfig = {};
module.exports = nextConfig;
JS

cat > frontend/.env.local.example <<'ENV'
NEXT_PUBLIC_API_BASE=http://localhost:8000/api
ENV

cat > frontend/lib/api.ts <<'TS'
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function apiPost<T>(path: string, body: any): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
TS

cat > frontend/lib/types.ts <<'TS'
export type FillProfile = {
  fill_profile_id: number;
  name: string;
  target_dry_kg_per_bag: number;
  target_water_kg_per_bag: number;
  notes?: string | null;
};

export type SubstrateBatch = {
  substrate_batch_id: number;
  name: string;
  substrate_recipe_version_id: number;
  fill_profile_id: number;
  bag_count: number;
  notes?: string | null;
};

export type SubstrateBag = {
  bag_id: string;
  substrate_batch_id: number;
  status: string;
  created_at: string;
};

export type HarvestEvent = {
  harvest_event_id: number;
  bag_id: string;
  flush_number: 1 | 2;
  fresh_weight_kg: number;
  harvested_at: string;
  notes?: string | null;
};

export type BagDetail = SubstrateBag & { harvest_events: HarvestEvent[] };

export type BatchMetrics = {
  substrate_batch_id: number;
  total_harvest_kg: number;
  dry_kg_total: number;
  be_percent: number;
};
TS

cat > frontend/app/styles.css <<'CSS'
body { font-family: system-ui, Arial, sans-serif; margin: 0; background: #f6f7f9; }
.container { max-width: 980px; margin: 0 auto; padding: 16px; }
.header { background: white; border-bottom: 1px solid #e6e8ee; }
.row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.brand { font-weight: 700; text-decoration: none; color: #111; }
.nav a { margin-left: 12px; color: #333; text-decoration: none; }
.card { background: white; border: 1px solid #e6e8ee; border-radius: 12px; padding: 16px; margin-top: 16px; }
.table { width: 100%; border-collapse: collapse; }
.table th, .table td { border-bottom: 1px solid #eee; padding: 8px; text-align: left; }
.btn { display: inline-block; padding: 8px 12px; border: 1px solid #111; border-radius: 10px; text-decoration: none; color: #111; background: #fff; }
.form { display: grid; gap: 12px; }
.form input, .form select { padding: 8px; border: 1px solid #ccc; border-radius: 8px; }
.error { color: #b00020; }
.kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 12px 0; }
.kpi { font-size: 22px; font-weight: 700; }
.kpiLabel { color: #666; font-size: 12px; }
.list { list-style: none; padding: 0; }
.list li { padding: 6px 0; border-bottom: 1px dashed #eee; }
CSS

cat > frontend/app/layout.tsx <<'TSX'
import "./styles.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="header">
          <div className="container row">
            <a className="brand" href="/">Mushroom Farm App</a>
            <nav className="nav">
              <a href="/batches">Batches</a>
              <a href="/batches/new">New Batch</a>
            </nav>
          </div>
        </header>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
TSX

cat > frontend/app/page.tsx <<'TSX'
export default function Home() {
  return (
    <div className="card">
      <h1>Welcome</h1>
      <p>MVP scaffold: create substrate batches, auto-generate bag IDs, log harvests (flush 1/2), compute BE% from fill-profile dry mass.</p>
    </div>
  );
}
TSX

cat > frontend/app/batches/page.tsx <<'TSX'
import { apiGet } from "../../lib/api";
import type { SubstrateBatch } from "../../lib/types";

export default async function Batches() {
  const batches = await apiGet<SubstrateBatch[]>("/batches");

  return (
    <div className="card">
      <h1>Batches</h1>
      <table className="table">
        <thead>
          <tr><th>ID</th><th>Name</th><th>Bags</th></tr>
        </thead>
        <tbody>
          {batches.map(b => (
            <tr key={b.substrate_batch_id}>
              <td>{b.substrate_batch_id}</td>
              <td><a href={`/batches/${b.substrate_batch_id}`}>{b.name}</a></td>
              <td>{b.bag_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p><a className="btn" href="/batches/new">Create new batch</a></p>
    </div>
  );
}
TSX

cat > frontend/app/batches/[batchId]/page.tsx <<'TSX'
import { apiGet } from "../../../lib/api";
import type { SubstrateBag, BatchMetrics } from "../../../lib/types";

export default async function BatchDetail({ params }: { params: { batchId: string } }) {
  const id = params.batchId;
  const bags = await apiGet<SubstrateBag[]>(`/batches/${id}/bags`);
  const metrics = await apiGet<BatchMetrics>(`/batches/${id}/metrics`);

  return (
    <div className="card">
      <h1>Batch {id}</h1>
      <div className="kpis">
        <div><div className="kpiLabel">Total Harvest (kg)</div><div className="kpi">{metrics.total_harvest_kg.toFixed(3)}</div></div>
        <div><div className="kpiLabel">Dry Mass Total (kg)</div><div className="kpi">{metrics.dry_kg_total.toFixed(3)}</div></div>
        <div><div className="kpiLabel">BE%</div><div className="kpi">{metrics.be_percent.toFixed(1)}</div></div>
      </div>

      <h2>Bags</h2>
      <ul className="list">
        {bags.map(b => (
          <li key={b.bag_id}>
            <a href={`/bags/${encodeURIComponent(b.bag_id)}`}>{b.bag_id}</a> — {b.status}
          </li>
        ))}
      </ul>
    </div>
  );
}
TSX

cat > frontend/app/batches/new/page.tsx <<'TSX'
"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../../../lib/api";
import type { FillProfile } from "../../../lib/types";

export default function NewBatch() {
  const [fillProfiles, setFillProfiles] = useState<FillProfile[]>([]);
  const [name, setName] = useState("");
  const [fillProfileId, setFillProfileId] = useState<number | null>(null);
  const [bagCount, setBagCount] = useState(10);
  const [recipeId, setRecipeId] = useState(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<FillProfile[]>("/fill-profiles")
      .then(fps => {
        setFillProfiles(fps);
        if (fps.length && fillProfileId === null) setFillProfileId(fps[0].fill_profile_id);
      })
      .catch(e => setError(String(e)));
  }, [fillProfileId]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const created = await apiPost<any>("/batches", {
        name,
        substrate_recipe_version_id: recipeId,
        fill_profile_id: fillProfileId,
        bag_count: bagCount
      });
      window.location.href = `/batches/${created.substrate_batch_id}`;
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Create Substrate Batch</h1>
      <form onSubmit={onSubmit} className="form">
        <label>
          Batch Name
          <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g., LM-2026-02-13-A" required />
        </label>

        <label>
          Fill Profile
          <select value={fillProfileId ?? ""} onChange={e => setFillProfileId(Number(e.target.value))}>
            {fillProfiles.map(fp => (
              <option key={fp.fill_profile_id} value={fp.fill_profile_id}>
                {fp.name} ({fp.target_dry_kg_per_bag}kg dry + {fp.target_water_kg_per_bag}kg water)
              </option>
            ))}
          </select>
        </label>

        <label>
          Bag Count
          <input type="number" min={1} value={bagCount} onChange={e => setBagCount(Number(e.target.value))} />
        </label>

        <label>
          Substrate Recipe Version ID
          <input type="number" min={1} value={recipeId} onChange={e => setRecipeId(Number(e.target.value))} />
        </label>

        <button className="btn" type="submit">Create Batch</button>
        {error && <p className="error">{error}</p>}
      </form>
    </div>
  );
}
TSX

cat > frontend/app/bags/[bagId]/page.tsx <<'TSX'
import { apiGet } from "../../../lib/api";
import type { BagDetail } from "../../../lib/types";

export default async function BagPage({ params }: { params: { bagId: string } }) {
  const bagId = decodeURIComponent(params.bagId);
  const bag = await apiGet<BagDetail>(`/bags/${encodeURIComponent(bagId)}`);

  return (
    <div className="card">
      <h1>Bag {bag.bag_id}</h1>
      <p>Status: {bag.status}</p>

      <h2>Harvest Events</h2>
      {bag.harvest_events.length === 0 ? (
        <p>No harvests logged.</p>
      ) : (
        <table className="table">
          <thead>
            <tr><th>Date</th><th>Flush</th><th>kg</th></tr>
          </thead>
          <tbody>
            {bag.harvest_events.map(h => (
              <tr key={h.harvest_event_id}>
                <td>{new Date(h.harvested_at).toLocaleString()}</td>
                <td>{h.flush_number}</td>
                <td>{h.fresh_weight_kg.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <p><a className="btn" href={`/bags/${encodeURIComponent(bag.bag_id)}/harvest`}>Log harvest</a></p>
    </div>
  );
}
TSX

cat > frontend/app/bags/[bagId]/harvest/page.tsx <<'TSX'
"use client";

import { useState } from "react";
import { apiPost } from "../../../../lib/api";

export default function LogHarvest({ params }: { params: { bagId: string } }) {
  const bagId = decodeURIComponent(params.bagId);
  const [flush, setFlush] = useState<1|2>(1);
  const [kg, setKg] = useState<number>(0.250);
  const [error, setError] = useState<string|null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiPost("/harvest-events", { bag_id: bagId, flush_number: flush, fresh_weight_kg: kg });
      window.location.href = `/bags/${encodeURIComponent(bagId)}`;
    } catch (e:any) {
      setError(e?.message || String(e));
    }
  }

  return (
    <div className="card">
      <h1>Log Harvest</h1>
      <p>Bag: {bagId}</p>
      <form onSubmit={submit} className="form">
        <label>
          Flush
          <select value={flush} onChange={e => setFlush(Number(e.target.value) as 1|2)}>
            <option value={1}>1</option>
            <option value={2}>2</option>
          </select>
        </label>
        <label>
          Fresh weight (kg)
          <input type="number" step="0.001" min="0" value={kg} onChange={e => setKg(Number(e.target.value))} />
        </label>
        <button className="btn" type="submit">Save</button>
        {error && <p className="error">{error}</p>}
      </form>
    </div>
  );
}
TSX

echo "Scaffold written successfully."
