"""Tests for bag-centric API."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, crud, schemas


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return Session()


def _seed_species(db):
    s = models.MushroomSpecies(code="LM", name="Lion's Mane", is_active=True)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _seed_substrate_recipe(db):
    r = models.SubstrateRecipeVersion(name="Masters Mix", recipe_code="MM", notes="")
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def _seed_spawn_recipe(db):
    r = models.SpawnRecipe(recipe_code="SR1", notes="")
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def _seed_fill_profile(db):
    f = models.FillProfile(name="Std", target_dry_kg_per_bag=1.0, target_water_kg_per_bag=1.25)
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def _seed_grain_type(db):
    g = models.GrainType(name="Rye")
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


def _seed_mix_lot(db, substrate_recipe, fill_profile):
    m = models.MixLot(
        lot_code="LOT1",
        substrate_recipe_version_id=substrate_recipe.substrate_recipe_version_id,
        fill_profile_id=fill_profile.fill_profile_id,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _seed_pasteurization_run(db, mix_lot, substrate_recipe):
    from datetime import datetime, timezone
    r = models.PasteurizationRun(
        run_code="PAST-001",
        mix_lot_id=mix_lot.mix_lot_id,
        substrate_recipe_version_id=substrate_recipe.substrate_recipe_version_id,
        unloaded_at=datetime.now(timezone.utc),
        bag_count=5,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def _seed_sterilization_run(db, spawn_recipe, grain_type):
    from datetime import datetime, timezone
    r = models.SterilizationRun(
        run_code="STER-001",
        spawn_recipe_id=spawn_recipe.spawn_recipe_id,
        grain_type_id=grain_type.grain_type_id,
        unloaded_at=datetime.now(timezone.utc),
        bag_count=5,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_create_spawn_bags():
    db = _session()
    try:
        species = _seed_species(db)
        spawn_recipe = _seed_spawn_recipe(db)
        grain_type = _seed_grain_type(db)
        ster_run = _seed_sterilization_run(db, spawn_recipe, grain_type)
        bags = crud.create_spawn_bags(db, ster_run.sterilization_run_id, species.species_id, 3)
        assert len(bags) == 3
        assert bags[0].bag_id.startswith("STER-")
        assert "SR1" in bags[0].bag_id
        assert "LM" in bags[0].bag_id
        assert bags[0].bag_type == "SPAWN"
    finally:
        db.close()


def test_create_substrate_bags():
    db = _session()
    try:
        species = _seed_species(db)
        sub_recipe = _seed_substrate_recipe(db)
        fill = _seed_fill_profile(db)
        mix = _seed_mix_lot(db, sub_recipe, fill)
        past_run = _seed_pasteurization_run(db, mix, sub_recipe)
        bags = crud.create_substrate_bags(db, past_run.pasteurization_run_id, species.species_id, 2)
        assert len(bags) == 2
        assert bags[0].bag_id.startswith("PAST-")
        assert "MM" in bags[0].bag_id
        assert bags[0].bag_type == "SUBSTRATE"
    finally:
        db.close()


def test_inoculation_and_harvest():
    db = _session()
    try:
        species = _seed_species(db)
        sub_recipe = _seed_substrate_recipe(db)
        fill = _seed_fill_profile(db)
        mix = _seed_mix_lot(db, sub_recipe, fill)
        past_run = _seed_pasteurization_run(db, mix, sub_recipe)
        spawn_recipe = _seed_spawn_recipe(db)
        grain_type = _seed_grain_type(db)
        ster_run = _seed_sterilization_run(db, spawn_recipe, grain_type)
        spawn_bags = crud.create_spawn_bags(db, ster_run.sterilization_run_id, species.species_id, 1)
        sub_bags = crud.create_substrate_bags(db, past_run.pasteurization_run_id, species.species_id, 1)
        spawn_bag = spawn_bags[0]
        sub_bag = sub_bags[0]
        inoc = crud.create_inoculation(db, sub_bag.bag_id, spawn_bag.bag_id)
        assert inoc.substrate_bag_id == sub_bag.bag_id
        ev1 = crud.create_harvest_event(db, sub_bag.bag_id, 1, 0.5)
        assert ev1.flush_number == 1
        ev2 = crud.create_harvest_event(db, sub_bag.bag_id, 2, 0.3)
        assert ev2.flush_number == 2
        total = crud.get_bag_total_harvest_kg(db, sub_bag.bag_id)
        assert total == pytest.approx(0.8)
    finally:
        db.close()


def test_harvest_duplicate_flush_raises():
    db = _session()
    try:
        species = _seed_species(db)
        sub_recipe = _seed_substrate_recipe(db)
        fill = _seed_fill_profile(db)
        mix = _seed_mix_lot(db, sub_recipe, fill)
        past_run = _seed_pasteurization_run(db, mix, sub_recipe)
        bags = crud.create_substrate_bags(db, past_run.pasteurization_run_id, species.species_id, 1)
        bag_id = bags[0].bag_id
        crud.create_harvest_event(db, bag_id, 1, 0.5)
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            crud.create_harvest_event(db, bag_id, 1, 0.4)
    finally:
        db.close()
