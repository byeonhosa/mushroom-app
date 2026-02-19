import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import api, crud, models, schemas


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    models.Base.metadata.create_all(bind=engine)
    return Session()


def test_species_create_and_list():
    db = _session()
    try:
        payload = schemas.MushroomSpeciesCreate(code="LM", name="Lion's Mane", latin_name="Hericium erinaceus")
        created = api.create_species(payload, db)
        assert created.species_id is not None
        assert created.code == "LM"

        rows = api.list_species(active_only=True, db=db)
        assert any(row.code == "LM" for row in rows)
    finally:
        db.close()


def test_harvest_flush_duplicate_returns_409():
    db = _session()
    try:
        species = crud.create_species(db, {"code": "OYS", "name": "Oyster"})
        block = crud.create_block(db, {"block_type": "SUBSTRATE", "species_id": species.species_id})

        first = schemas.HarvestEventCreate(block_id=block.block_id, flush_number=1, fresh_weight_kg=0.5, notes="first")
        created = api.create_harvest(first, db)
        assert created.harvest_event_id is not None

        duplicate = schemas.HarvestEventCreate(block_id=block.block_id, flush_number=1, fresh_weight_kg=0.4, notes="dup")
        with pytest.raises(HTTPException) as exc:
            api.create_harvest(duplicate, db)
        assert exc.value.status_code == 409
        assert exc.value.detail == "Flush already recorded for this block."
    finally:
        db.close()
