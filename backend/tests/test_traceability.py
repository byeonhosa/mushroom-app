"""Tests for run detail and spawn lineage traceability views."""

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


def _seed_species(db):
    row = models.MushroomSpecies(code="LM", name="Lion's Mane", is_active=True)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_liquid_culture(db, species):
    row = models.LiquidCulture(
        culture_code="LC-001",
        species_id=species.species_id,
        source="Internal lab",
        is_active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_spawn_recipe(db):
    row = models.SpawnRecipe(recipe_code="SR1", notes="")
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


def _seed_substrate_recipe(db):
    row = models.SubstrateRecipeVersion(name="Masters Mix", recipe_code="MM", notes="")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_fill_profile(db):
    row = models.FillProfile(name="Std", target_dry_kg_per_bag=1.25, target_water_kg_per_bag=1.6)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_sterilization_run(db, spawn_recipe, grain_type):
    row = models.SterilizationRun(
        run_code="STER-001",
        spawn_recipe_id=spawn_recipe.spawn_recipe_id,
        grain_type_id=grain_type.grain_type_id,
        unloaded_at=datetime.now(timezone.utc),
        bag_count=8,
    )
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


def _seed_pasteurization_run(db, mix_lot, substrate_recipe):
    row = models.PasteurizationRun(
        run_code="PAST-001",
        mix_lot_id=mix_lot.mix_lot_id,
        substrate_recipe_version_id=substrate_recipe.substrate_recipe_version_id,
        unloaded_at=datetime.now(timezone.utc),
        bag_count=8,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _prepare_traceability_flow(db):
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

    substrate_recipe = _seed_substrate_recipe(db)
    fill_profile = _seed_fill_profile(db)
    mix_lot = _seed_mix_lot(db, substrate_recipe, fill_profile)
    pasteurization_run = _seed_pasteurization_run(db, mix_lot, substrate_recipe)
    crud.create_substrate_bags(db, pasteurization_run.pasteurization_run_id, 2)
    child_bags = crud.create_inoculation_batch(
        db,
        pasteurization_run.pasteurization_run_id,
        2,
        spawn_bag.bag_code,
    )

    first_child, second_child = child_bags
    crud.update_bag_incubation_start(db, first_child.bag_code)
    crud.update_bag_ready(db, first_child.bag_code)
    crud.update_bag_fruiting_start(db, first_child.bag_code)
    crud.create_harvest_event(db, first_child.bag_code, 1, 0.75)
    crud.update_bag_disposal(db, second_child.bag_code, "CONTAMINATION")

    return sterilization_run, pasteurization_run, spawn_bag, first_child, second_child


def test_spawn_bag_detail_includes_child_lineage_summary():
    db = _session()
    try:
        _, _, spawn_bag, first_child, second_child = _prepare_traceability_flow(db)

        detail = crud.get_bag_detail(db, spawn_bag.bag_code)

        assert detail is not None
        assert detail["bag_ref"] == spawn_bag.bag_code
        assert detail["child_summary"]["total_bags"] == 2
        assert detail["child_summary"]["contaminated_bags"] == 1
        assert detail["child_summary"]["harvested_bags"] == 1
        assert detail["child_summary"]["total_harvest_kg"] == pytest.approx(0.75)

        child_rows = {row["bag_ref"]: row for row in detail["child_bags"]}
        assert set(child_rows) == {first_child.bag_code, second_child.bag_code}
        assert all(row["generation"] == 1 for row in child_rows.values())
        assert child_rows[first_child.bag_code]["total_harvest_kg"] == pytest.approx(0.75)
        assert child_rows[second_child.bag_code]["contaminated"] is True
    finally:
        db.close()


def test_spawn_to_spawn_lineage_surfaces_descendants_across_generations():
    db = _session()
    try:
        species = _seed_species(db)
        liquid_culture = _seed_liquid_culture(db, species)
        root_spawn_recipe = _seed_spawn_recipe(db)
        root_grain_type = _seed_grain_type(db)
        root_run = _seed_sterilization_run(db, root_spawn_recipe, root_grain_type)
        crud.create_spawn_bags(db, root_run.sterilization_run_id, 1)
        root_spawn = crud.inoculate_spawn_bags(
            db,
            root_run.sterilization_run_id,
            1,
            models.InoculationSourceType.LIQUID_CULTURE.value,
            liquid_culture_id=liquid_culture.liquid_culture_id,
        )[0]
        crud.update_bag_incubation_start(db, root_spawn.bag_code)
        root_spawn = crud.update_bag_ready(db, root_spawn.bag_code)

        child_spawn_recipe = models.SpawnRecipe(recipe_code="SR2", notes="")
        child_grain_type = models.GrainType(name="Millet")
        db.add(child_spawn_recipe)
        db.add(child_grain_type)
        db.commit()
        db.refresh(child_spawn_recipe)
        db.refresh(child_grain_type)

        child_run = models.SterilizationRun(
            run_code="STER-002",
            spawn_recipe_id=child_spawn_recipe.spawn_recipe_id,
            grain_type_id=child_grain_type.grain_type_id,
            unloaded_at=datetime.now(timezone.utc),
            bag_count=3,
        )
        db.add(child_run)
        db.commit()
        db.refresh(child_run)

        crud.create_spawn_bags(db, child_run.sterilization_run_id, 1)
        child_spawn = crud.inoculate_spawn_bags(
            db,
            child_run.sterilization_run_id,
            1,
            models.InoculationSourceType.SPAWN_BAG.value,
            donor_spawn_bag_ref=root_spawn.bag_code,
        )[0]
        crud.update_bag_incubation_start(db, child_spawn.bag_code)
        child_spawn = crud.update_bag_ready(db, child_spawn.bag_code)

        substrate_recipe = _seed_substrate_recipe(db)
        fill_profile = _seed_fill_profile(db)
        mix_lot = _seed_mix_lot(db, substrate_recipe, fill_profile)
        pasteurization_run = _seed_pasteurization_run(db, mix_lot, substrate_recipe)
        crud.create_substrate_bags(db, pasteurization_run.pasteurization_run_id, 1)
        substrate_bag = crud.create_inoculation_batch(
            db,
            pasteurization_run.pasteurization_run_id,
            1,
            child_spawn.bag_code,
        )[0]

        detail = crud.get_bag_detail(db, root_spawn.bag_code)
        run_detail = crud.get_sterilization_run_detail(db, root_run.sterilization_run_id)

        assert detail is not None
        lineage_by_ref = {row["bag_ref"]: row for row in detail["child_bags"]}
        assert lineage_by_ref[child_spawn.bag_code]["generation"] == 1
        assert lineage_by_ref[child_spawn.bag_code]["bag_type"] == "SPAWN"
        assert lineage_by_ref[substrate_bag.bag_code]["generation"] == 2
        assert lineage_by_ref[substrate_bag.bag_code]["bag_type"] == "SUBSTRATE"

        assert run_detail is not None
        downstream_rows = {row["bag_ref"]: row for row in run_detail["downstream_substrate_bags"]}
        assert substrate_bag.bag_code in downstream_rows
        assert run_detail["downstream_summary"]["total_bags"] == 1
    finally:
        db.close()


def test_sterilization_run_detail_includes_downstream_outcomes():
    db = _session()
    try:
        sterilization_run, _, spawn_bag, first_child, second_child = _prepare_traceability_flow(db)

        detail = crud.get_sterilization_run_detail(db, sterilization_run.sterilization_run_id)

        assert detail is not None
        assert detail["run_code"] == sterilization_run.run_code
        assert detail["summary"]["total_bags"] == 1
        assert detail["summary"]["consumed_bags"] == 1
        assert detail["downstream_summary"]["total_bags"] == 2
        assert detail["downstream_summary"]["contaminated_bags"] == 1
        assert detail["downstream_summary"]["harvested_bags"] == 1

        downstream_rows = {row["bag_ref"]: row for row in detail["downstream_substrate_bags"]}
        assert downstream_rows[first_child.bag_code]["parent_spawn_bag_ref"] == spawn_bag.bag_code
        assert downstream_rows[second_child.bag_code]["source_sterilization_run_code"] == sterilization_run.run_code
    finally:
        db.close()


def test_pasteurization_run_detail_includes_bag_metrics_and_sources():
    db = _session()
    try:
        _, pasteurization_run, _, first_child, second_child = _prepare_traceability_flow(db)
        crud.update_bag_actual_dry_weight(db, first_child.bag_code, 1.0)

        detail = crud.get_pasteurization_run_detail(db, pasteurization_run.pasteurization_run_id)

        assert detail is not None
        assert detail["run_code"] == pasteurization_run.run_code
        assert detail["summary"]["total_bags"] == 2
        assert detail["summary"]["contaminated_bags"] == 1
        assert detail["summary"]["harvested_bags"] == 1

        bag_rows = {row["bag_ref"]: row for row in detail["bags"]}
        assert bag_rows[first_child.bag_code]["dry_weight_source"] == "ACTUAL"
        assert bag_rows[first_child.bag_code]["bio_efficiency"] == pytest.approx(0.75)
        assert bag_rows[second_child.bag_code]["contaminated"] is True
        assert bag_rows[second_child.bag_code]["pasteurization_run_code"] == pasteurization_run.run_code
    finally:
        db.close()
