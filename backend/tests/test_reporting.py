"""Tests for biological-efficiency and contamination reporting."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import crud, models


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return Session()


def _seed_species(db, *, code: str = "LM", name: str = "Lion's Mane"):
    row = models.MushroomSpecies(code=code, name=name, is_active=True)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_liquid_culture(db, species, *, culture_code: str = "LC-001"):
    row = models.LiquidCulture(
        culture_code=culture_code,
        species_id=species.species_id,
        source="Internal lab",
        is_active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_substrate_recipe(db, *, recipe_code: str = "MM"):
    row = models.SubstrateRecipeVersion(name="Masters Mix", recipe_code=recipe_code, notes="")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_spawn_recipe(db, *, recipe_code: str = "SR1"):
    row = models.SpawnRecipe(recipe_code=recipe_code, notes="")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_fill_profile(db, *, target_dry_kg_per_bag: float = 1.25):
    row = models.FillProfile(
        name="Std",
        target_dry_kg_per_bag=target_dry_kg_per_bag,
        target_water_kg_per_bag=1.6,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_grain_type(db):
    row = models.GrainType(name="Rye")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_mix_lot(db, substrate_recipe, fill_profile):
    row = models.MixLot(
        lot_code="LOT1",
        substrate_recipe_version_id=substrate_recipe.substrate_recipe_version_id,
        fill_profile_id=fill_profile.fill_profile_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_pasteurization_run(db, mix_lot, substrate_recipe, *, run_code: str = "PAST-001"):
    row = models.PasteurizationRun(
        run_code=run_code,
        mix_lot_id=mix_lot.mix_lot_id,
        substrate_recipe_version_id=substrate_recipe.substrate_recipe_version_id,
        unloaded_at=datetime.now(timezone.utc),
        bag_count=10,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_sterilization_run(db, spawn_recipe, grain_type, *, run_code: str = "STER-001"):
    row = models.SterilizationRun(
        run_code=run_code,
        spawn_recipe_id=spawn_recipe.spawn_recipe_id,
        grain_type_id=grain_type.grain_type_id,
        unloaded_at=datetime.now(timezone.utc),
        bag_count=10,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _prepare_ready_spawn(db):
    species = _seed_species(db)
    liquid_culture = _seed_liquid_culture(db, species)
    spawn_recipe = _seed_spawn_recipe(db)
    grain_type = _seed_grain_type(db)
    sterilization_run = _seed_sterilization_run(db, spawn_recipe, grain_type)
    crud.create_spawn_bags(db, sterilization_run.sterilization_run_id, 1)
    spawn_bag = crud.inoculate_spawn_bags(
        db,
        sterilization_run.sterilization_run_id,
        1,
        models.InoculationSourceType.LIQUID_CULTURE.value,
        liquid_culture_id=liquid_culture.liquid_culture_id,
    )[0]
    crud.update_bag_incubation_start(db, spawn_bag.bag_code)
    spawn_bag = crud.update_bag_ready(db, spawn_bag.bag_code)
    return species, sterilization_run, spawn_bag


def _prepare_inoculated_substrate_batch(db, *, bag_count: int = 3):
    species, sterilization_run, spawn_bag = _prepare_ready_spawn(db)
    substrate_recipe = _seed_substrate_recipe(db)
    fill_profile = _seed_fill_profile(db)
    mix_lot = _seed_mix_lot(db, substrate_recipe, fill_profile)
    pasteurization_run = _seed_pasteurization_run(db, mix_lot, substrate_recipe)
    crud.create_substrate_bags(db, pasteurization_run.pasteurization_run_id, bag_count)
    substrate_bags = crud.create_inoculation_batch(
        db,
        pasteurization_run.pasteurization_run_id,
        bag_count,
        spawn_bag.bag_code,
    )
    return species, sterilization_run, pasteurization_run, spawn_bag, substrate_bags


def test_create_substrate_bags_snapshots_target_and_optional_actual_dry_weight():
    db = _session()
    try:
        substrate_recipe = _seed_substrate_recipe(db)
        fill_profile = _seed_fill_profile(db, target_dry_kg_per_bag=1.4)
        mix_lot = _seed_mix_lot(db, substrate_recipe, fill_profile)
        pasteurization_run = _seed_pasteurization_run(db, mix_lot, substrate_recipe)

        bags = crud.create_substrate_bags(
            db,
            pasteurization_run.pasteurization_run_id,
            2,
            actual_dry_kg=1.5,
        )

        assert [float(bag.target_dry_kg) for bag in bags] == [pytest.approx(1.4), pytest.approx(1.4)]
        assert [float(bag.actual_dry_kg) for bag in bags] == [pytest.approx(1.5), pytest.approx(1.5)]
        assert all(bag.dry_weight_source == "ACTUAL" for bag in bags)
        assert all(bag.dry_weight_kg == pytest.approx(1.5) for bag in bags)
    finally:
        db.close()


def test_calculate_bio_efficiency_prefers_actual_over_target():
    bio_efficiency, dry_weight_kg, dry_weight_source = crud.calculate_bio_efficiency(
        0.85,
        actual_dry_kg=1.0,
        target_dry_kg=1.25,
    )

    assert bio_efficiency == pytest.approx(0.85)
    assert dry_weight_kg == pytest.approx(1.0)
    assert dry_weight_source == "ACTUAL"


def test_production_report_includes_be_and_contamination_summaries():
    db = _session()
    try:
        _, sterilization_run, pasteurization_run, spawn_bag, substrate_bags = _prepare_inoculated_substrate_batch(db)
        bag_one, bag_two, bag_three = substrate_bags

        crud.update_bag_actual_dry_weight(db, bag_one.bag_code, 1.0)

        for bag in (bag_one, bag_two):
            crud.update_bag_incubation_start(db, bag.bag_code)
            crud.update_bag_ready(db, bag.bag_code)
            crud.update_bag_fruiting_start(db, bag.bag_code)

        crud.create_harvest_event(db, bag_one.bag_code, 1, 0.8)
        crud.create_harvest_event(db, bag_two.bag_code, 1, 0.625)
        crud.update_bag_disposal(db, bag_three.bag_code, "CONTAMINATION")

        report = crud.get_production_report(db)

        assert report["summary"]["total_spawn_bags"] == 1
        assert report["summary"]["total_substrate_bags"] == 3
        assert report["summary"]["total_contaminated_bags"] == 1
        assert report["summary"]["total_harvest_kg"] == pytest.approx(1.425)
        assert report["summary"]["total_dry_weight_kg"] == pytest.approx(3.5)
        assert report["summary"]["overall_bio_efficiency"] == pytest.approx(1.425 / 3.5)

        rows_by_ref = {row["bag_ref"]: row for row in report["substrate_bags"]}
        assert rows_by_ref[bag_one.bag_code]["dry_weight_source"] == "ACTUAL"
        assert rows_by_ref[bag_one.bag_code]["bio_efficiency"] == pytest.approx(0.8)
        assert rows_by_ref[bag_two.bag_code]["dry_weight_source"] == "TARGET"
        assert rows_by_ref[bag_two.bag_code]["bio_efficiency"] == pytest.approx(0.5)
        assert rows_by_ref[bag_three.bag_code]["contaminated"] is True

        by_parent_spawn = report["contamination_by_parent_spawn_bag"]
        assert by_parent_spawn == [
            {
                "key": spawn_bag.bag_id,
                "label": spawn_bag.bag_code,
                "total_bags": 3,
                "contaminated_bags": 1,
                "contamination_rate": pytest.approx(1 / 3),
            }
        ]

        by_pasteurization = report["contamination_by_pasteurization_run"]
        assert by_pasteurization == [
            {
                "key": str(pasteurization_run.pasteurization_run_id),
                "label": pasteurization_run.run_code,
                "total_bags": 3,
                "contaminated_bags": 1,
                "contamination_rate": pytest.approx(1 / 3),
            }
        ]

        by_source_sterilization = report["contamination_by_source_sterilization_run"]
        assert by_source_sterilization[0]["label"] == sterilization_run.run_code
        assert by_source_sterilization[0]["total_bags"] == 4
        assert by_source_sterilization[0]["contaminated_bags"] == 1

        run_metrics = report["pasteurization_runs"]
        assert run_metrics == [
            {
                "pasteurization_run_id": pasteurization_run.pasteurization_run_id,
                "run_code": pasteurization_run.run_code,
                "total_bags": 3,
                "contaminated_bags": 1,
                "contamination_rate": pytest.approx(1 / 3),
                "total_harvest_kg": pytest.approx(1.425),
                "total_dry_weight_kg": pytest.approx(3.5),
                "bio_efficiency": pytest.approx(1.425 / 3.5),
            }
        ]
    finally:
        db.close()
