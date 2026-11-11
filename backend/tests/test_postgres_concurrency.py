"""Two people working at the same moment (SRS BAG-11). PostgreSQL only.

SQLite has a single writer, so these can only be proved against the database
the farm runs on. CI runs this file in the `migration-smoke` job; locally it is
skipped unless DATABASE_URL points at PostgreSQL.
"""

import os
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app import crud, models
from app.migrate import MIG_DIR, apply_migration, ensure_schema_migrations

WORKERS = 8


@pytest.fixture
def pg_sessions():
    """A session factory on a throwaway PostgreSQL database built by the migrations."""
    base_url = make_url(os.environ["DATABASE_URL"])
    if base_url.get_backend_name() != "postgresql":
        pytest.skip("Concurrency tests require PostgreSQL.")

    name = f"mushroom_concurrency_{uuid.uuid4().hex[:10]}"
    assert re.fullmatch(r"[a-z0-9_]+", name)
    admin = create_engine(
        base_url.set(database="postgres").render_as_string(hide_password=False),
        isolation_level="AUTOCOMMIT",
    )
    with admin.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {name}"))
    engine = create_engine(
        base_url.set(database=name).render_as_string(hide_password=False),
        pool_size=WORKERS + 2,
        max_overflow=0,
    )
    try:
        ensure_schema_migrations(engine)
        for migration in sorted(MIG_DIR.glob("*.sql")):
            apply_migration(engine, migration.name, migration.read_text(encoding="utf-8"))
        yield sessionmaker(bind=engine, autocommit=False, autoflush=False)
    finally:
        engine.dispose()
        with admin.connect() as conn:
            conn.execute(
                text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :n AND pid <> pg_backend_pid()"),
                {"n": name},
            )
            conn.execute(text(f"DROP DATABASE IF EXISTS {name}"))
        admin.dispose()


def _seed(Session):
    """Reference rows, one sterilization run and one pasteurization run of 400 bags each."""
    now = datetime.now(timezone.utc)
    with Session() as db:
        species = db.query(models.MushroomSpecies).filter_by(code="LM").one_or_none()
        if species is None:
            species = models.MushroomSpecies(code="LM", name="Lion's Mane", is_active=True)
            db.add(species)
        spawn_recipe = db.query(models.SpawnRecipe).first() or models.SpawnRecipe(recipe_code="SRX")
        grain = db.query(models.GrainType).first() or models.GrainType(name="Rye X")
        substrate_recipe = db.query(models.SubstrateRecipeVersion).first() or models.SubstrateRecipeVersion(
            name="Mix X", recipe_code="MX"
        )
        fill_profile = db.query(models.FillProfile).first() or models.FillProfile(
            name="Fill X", target_dry_kg_per_bag=1, target_water_kg_per_bag=1
        )
        db.add_all([spawn_recipe, grain, substrate_recipe, fill_profile])
        db.flush()
        culture = models.LiquidCulture(culture_code="LC-CONC", species_id=species.species_id, is_active=True)
        mix_lot = models.MixLot(
            lot_code="LOT-CONC",
            substrate_recipe_version_id=substrate_recipe.substrate_recipe_version_id,
            fill_profile_id=fill_profile.fill_profile_id,
        )
        db.add_all([culture, mix_lot])
        db.flush()
        sterilization = models.SterilizationRun(
            run_code="261109A",
            spawn_recipe_id=spawn_recipe.spawn_recipe_id,
            grain_type_id=grain.grain_type_id,
            unloaded_at=now,
            bag_count=400,
        )
        pasteurization = models.PasteurizationRun(
            run_code="261109A",
            mix_lot_id=mix_lot.mix_lot_id,
            substrate_recipe_version_id=substrate_recipe.substrate_recipe_version_id,
            unloaded_at=now,
            bag_count=400,
        )
        db.add_all([sterilization, pasteurization])
        db.commit()
        return {
            "sterilization_run_id": sterilization.sterilization_run_id,
            "pasteurization_run_id": pasteurization.pasteurization_run_id,
            "liquid_culture_id": culture.liquid_culture_id,
        }


def _run_together(Session, work, jobs):
    """Run `work(db, job)` for every job at once, each in its own session, released together."""
    start = threading.Barrier(len(jobs))

    def call(job):
        with Session() as db:
            start.wait(timeout=30)
            return work(db, job)

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = [pool.submit(call, job) for job in jobs]
        # .result() re-raises: any error in any worker fails the test.
        return [future.result(timeout=120) for future in futures]


def test_bag_records_created_at_the_same_moment_get_different_ids(pg_sessions):
    ids = _seed(pg_sessions)

    def create(db, job):
        kind, count = job
        if kind == "spawn":
            bags = crud.create_spawn_bags(db, ids["sterilization_run_id"], count)
        else:
            bags = crud.create_substrate_bags(db, ids["pasteurization_run_id"], count)
        return [bag.bag_id for bag in bags]

    jobs = [("spawn", 7), ("substrate", 5)] * (WORKERS // 2)
    results = _run_together(pg_sessions, create, jobs)

    spawn_ids = [bag_id for job, created in zip(jobs, results) if job[0] == "spawn" for bag_id in created]
    substrate_ids = [bag_id for job, created in zip(jobs, results) if job[0] == "substrate" for bag_id in created]
    assert len(spawn_ids) == len(set(spawn_ids)) == 7 * (WORKERS // 2)
    assert len(substrate_ids) == len(set(substrate_ids)) == 5 * (WORKERS // 2)
    # No gaps either: the numbers handed out are exactly 1..n.
    assert sorted(int(i.split("-")[1]) for i in spawn_ids) == list(range(1, len(spawn_ids) + 1))
    assert sorted(int(i.split("-")[1]) for i in substrate_ids) == list(range(1, len(substrate_ids) + 1))


def test_inoculation_sessions_on_one_run_at_the_same_moment_get_different_bag_codes(pg_sessions):
    ids = _seed(pg_sessions)
    per_session = 5
    with pg_sessions() as db:
        crud.create_spawn_bags(db, ids["sterilization_run_id"], per_session * WORKERS)

    def inoculate(db, job):
        bags = crud.inoculate_spawn_bags(
            db,
            ids["sterilization_run_id"],
            per_session,
            "LIQUID_CULTURE",
            liquid_culture_id=ids["liquid_culture_id"],
        )
        return [(bag.bag_id, bag.bag_code) for bag in bags]

    results = _run_together(pg_sessions, inoculate, list(range(WORKERS)))
    pairs = [pair for session in results for pair in session]

    codes = [code for _, code in pairs]
    bag_ids = [bag_id for bag_id, _ in pairs]
    assert len(codes) == len(set(codes)) == per_session * WORKERS
    # No bag was inoculated by two sessions.
    assert len(bag_ids) == len(set(bag_ids)) == per_session * WORKERS
    assert sorted(int(code.rsplit("-", 1)[1]) for code in codes) == list(range(1, len(codes) + 1))

    with pg_sessions() as db:
        labeled = db.query(models.Bag).filter(models.Bag.bag_code.is_not(None)).count()
        assert labeled == per_session * WORKERS
