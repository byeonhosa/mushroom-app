"""Tests for the species_profiles table and its JSON seeder."""

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.seed_species import load_seed_records, seed


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return Session()


def test_table_is_created():
    db = _session()
    assert "species_profiles" in inspect(db.get_bind()).get_table_names()
    assert db.query(models.SpeciesProfile).count() == 0


def test_seed_loads_all_species():
    db = _session()
    count = seed(db)

    assert count == 8
    assert db.query(models.SpeciesProfile).count() == 8

    reishi = (
        db.query(models.SpeciesProfile)
        .filter(models.SpeciesProfile.code == "reishi")
        .one()
    )
    assert reishi.common_name == "Reishi"
    assert reishi.fruiting_temp_f_low == 72
    assert reishi.difficulty_rank == 4


def test_seed_is_idempotent():
    db = _session()
    seed(db)
    seed(db)
    assert db.query(models.SpeciesProfile).count() == 8


def test_json_nulls_preserved_as_sql_null():
    db = _session()
    seed(db)

    # Oyster has null substrate_moisture in the source but a real BE figure.
    oyster = (
        db.query(models.SpeciesProfile)
        .filter(models.SpeciesProfile.code == "oyster")
        .one()
    )
    assert oyster.substrate_moisture_pct_low is None
    assert oyster.substrate_moisture_pct_high is None
    assert oyster.biological_efficiency_pct_low == 100

    # Lion's Mane has null biological efficiency — must stay NULL, not 0.
    lions_mane = (
        db.query(models.SpeciesProfile)
        .filter(models.SpeciesProfile.code == "lions_mane")
        .one()
    )
    assert lions_mane.biological_efficiency_pct_low is None
    assert lions_mane.biological_efficiency_pct_high is None


def test_model_columns_match_json_keys():
    # Every seed key (besides the id->code remap) must be a real model column.
    record = load_seed_records()[0]
    columns = set(inspect(models.SpeciesProfile).columns.keys())
    for key in record:
        column = "code" if key == "id" else key
        assert column in columns, f"missing column for JSON key {key!r}"
