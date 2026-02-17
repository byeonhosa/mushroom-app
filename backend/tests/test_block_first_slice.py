from datetime import datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from app import models, crud, schemas


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    models.Base.metadata.create_all(bind=engine)
    return Session()


def _seed_substrate_batch(db):
    recipe = models.SubstrateRecipeVersion(name="Recipe A")
    fill = models.FillProfile(name="Fill A", target_dry_kg_per_bag=1.0, target_water_kg_per_bag=1.0)
    db.add_all([recipe, fill])
    db.commit()
    db.refresh(recipe)
    db.refresh(fill)
    batch = models.SubstrateBatch(
        name="BATCH-A",
        substrate_recipe_version_id=recipe.substrate_recipe_version_id,
        fill_profile_id=fill.fill_profile_id,
        bag_count=1,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def test_block_code_generation_unique_per_day_prefix():
    db = _session()
    try:
        b1 = crud.create_block(db, {"block_type": "SPAWN"})
        b2 = crud.create_block(db, {"block_type": "SPAWN"})
        assert b1.block_code.startswith("SP-")
        assert b2.block_code.startswith("SP-")
        assert b1.block_code != b2.block_code
    finally:
        db.close()


def test_inoculation_unique_child_constraint():
    db = _session()
    try:
        parent = crud.create_block(db, {"block_type": "SPAWN"})
        child = crud.create_block(db, {"block_type": "SUBSTRATE"})
        first = crud.create_inoculation(
            db, {"child_block_id": child.block_id, "parent_spawn_block_id": parent.block_id}
        )
        assert first["child_block_id"] == child.block_id
        with pytest.raises(IntegrityError):
            crud.create_inoculation(
                db, {"child_block_id": child.block_id, "parent_spawn_block_id": parent.block_id}
            )
    finally:
        db.close()


def test_harvest_event_validation_and_creation():
    db = _session()
    try:
        with pytest.raises(ValidationError):
            schemas.HarvestEventCreate(flush_number=1, fresh_weight_kg=0.5)  # missing block_id

        spawn_block = crud.create_block(db, {"block_type": "SPAWN"})
        with pytest.raises(ValueError):
            crud.create_harvest_event(
                db, {"block_id": spawn_block.block_id, "flush_number": 1, "fresh_weight_kg": 0.5}
            )

        batch = _seed_substrate_batch(db)
        substrate_block = crud.create_block(
            db, {"block_type": "SUBSTRATE", "substrate_batch_id": batch.substrate_batch_id}
        )
        event = crud.create_harvest_event(
            db,
            {
                "block_id": substrate_block.block_id,
                "flush_number": 1,
                "fresh_weight_kg": 0.5,
                "harvested_at": datetime.utcnow(),
                "notes": "ok",
            },
        )
        assert event.harvest_event_id is not None
        assert event.block_id == substrate_block.block_id
        assert float(event.fresh_weight_kg) == pytest.approx(0.5)
    finally:
        db.close()
