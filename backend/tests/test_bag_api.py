"""Workflow tests for unlabeled bag records and inoculation-driven bag codes."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
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


def _seed_liquid_culture(db, species, *, culture_code: str = "LC-001", source: str = "Internal lab"):
    row = models.LiquidCulture(
        culture_code=culture_code,
        species_id=species.species_id,
        source=source,
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


def _seed_fill_profile(db):
    row = models.FillProfile(name="Std", target_dry_kg_per_bag=1.0, target_water_kg_per_bag=1.25)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_grain_type(db, *, name: str = "Rye"):
    row = models.GrainType(name=name)
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
        bag_count=12,
    )
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
        bag_count=12,
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
    spawn_bag = crud.update_bag_incubation_start(db, spawn_bag.bag_code)
    spawn_bag = crud.update_bag_ready(db, spawn_bag.bag_code)
    return species, sterilization_run, spawn_bag, liquid_culture


def _prepare_inoculated_substrate(db):
    species, _, spawn_bag, _ = _prepare_ready_spawn(db)
    substrate_recipe = _seed_substrate_recipe(db)
    fill_profile = _seed_fill_profile(db)
    mix_lot = _seed_mix_lot(db, substrate_recipe, fill_profile)
    pasteurization_run = _seed_pasteurization_run(db, mix_lot, substrate_recipe)
    crud.create_substrate_bags(db, pasteurization_run.pasteurization_run_id, 1)
    substrate_bag = crud.create_inoculation_batch(
        db,
        pasteurization_run.pasteurization_run_id,
        1,
        spawn_bag.bag_code,
    )[0]
    return species, spawn_bag, pasteurization_run, substrate_bag


def test_create_spawn_bags_creates_unlabeled_internal_records():
    db = _session()
    try:
        spawn_recipe = _seed_spawn_recipe(db)
        grain_type = _seed_grain_type(db)
        sterilization_run = _seed_sterilization_run(db, spawn_recipe, grain_type)

        first_batch = crud.create_spawn_bags(db, sterilization_run.sterilization_run_id, 3)
        second_batch = crud.create_spawn_bags(db, sterilization_run.sterilization_run_id, 2)

        assert [bag.bag_id for bag in first_batch] == ["SPNREC-0001", "SPNREC-0002", "SPNREC-0003"]
        assert [bag.bag_id for bag in second_batch] == ["SPNREC-0004", "SPNREC-0005"]
        assert all(bag.bag_code is None for bag in first_batch + second_batch)
        assert all(bag.species_id is None for bag in first_batch + second_batch)
        assert all(bag.status == "STERILIZED" for bag in first_batch + second_batch)
    finally:
        db.close()


def test_spawn_inoculation_assigns_unique_printable_codes_across_batches():
    db = _session()
    try:
        species = _seed_species(db)
        liquid_culture = _seed_liquid_culture(db, species)
        spawn_recipe = _seed_spawn_recipe(db)
        grain_type = _seed_grain_type(db)
        sterilization_run = _seed_sterilization_run(db, spawn_recipe, grain_type)

        crud.create_spawn_bags(db, sterilization_run.sterilization_run_id, 4)
        first_inoculation = crud.inoculate_spawn_bags(
            db,
            sterilization_run.sterilization_run_id,
            2,
            models.InoculationSourceType.LIQUID_CULTURE.value,
            liquid_culture_id=liquid_culture.liquid_culture_id,
        )
        second_inoculation = crud.inoculate_spawn_bags(
            db,
            sterilization_run.sterilization_run_id,
            2,
            models.InoculationSourceType.LIQUID_CULTURE.value,
            liquid_culture_id=liquid_culture.liquid_culture_id,
        )

        bag_codes = [bag.bag_code for bag in first_inoculation + second_inoculation]

        assert bag_codes == [
            "STER-STER-001-SR1-LM-0001",
            "STER-STER-001-SR1-LM-0002",
            "STER-STER-001-SR1-LM-0003",
            "STER-STER-001-SR1-LM-0004",
        ]
        assert all(bag.bag_ref == bag.bag_code for bag in first_inoculation + second_inoculation)
        assert all(bag.labeled_at is not None for bag in first_inoculation + second_inoculation)
        assert all(bag.status == "INOCULATED" for bag in first_inoculation + second_inoculation)
        assert all(bag.source_liquid_culture_id == liquid_culture.liquid_culture_id for bag in first_inoculation + second_inoculation)
        assert all(bag.inoculation_source_type == "LIQUID_CULTURE" for bag in first_inoculation + second_inoculation)
    finally:
        db.close()


def test_spawn_to_spawn_inoculation_assigns_lineage_and_consumes_donor():
    db = _session()
    try:
        _, donor_run, donor_spawn, liquid_culture = _prepare_ready_spawn(db)
        second_spawn_recipe = _seed_spawn_recipe(db, recipe_code="SR2")
        grain_type = _seed_grain_type(db, name="Millet")
        child_run = models.SterilizationRun(
            run_code="STER-002",
            spawn_recipe_id=second_spawn_recipe.spawn_recipe_id,
            grain_type_id=grain_type.grain_type_id,
            unloaded_at=datetime.now(timezone.utc),
            bag_count=4,
        )
        db.add(child_run)
        db.commit()
        db.refresh(child_run)

        crud.create_spawn_bags(db, child_run.sterilization_run_id, 2)
        child_bags = crud.inoculate_spawn_bags(
            db,
            child_run.sterilization_run_id,
            2,
            models.InoculationSourceType.SPAWN_BAG.value,
            donor_spawn_bag_ref=donor_spawn.bag_code,
        )
        refreshed_donor = crud.get_bag(db, donor_spawn.bag_code)
        donor_detail = crud.get_bag_detail(db, donor_spawn.bag_code)

        assert all(bag.parent_spawn_bag_id == donor_spawn.bag_id for bag in child_bags)
        assert all(bag.source_liquid_culture_id is None for bag in child_bags)
        assert all(bag.inoculation_source_type == "SPAWN_BAG" for bag in child_bags)
        assert refreshed_donor is not None
        assert refreshed_donor.status == "CONSUMED"
        assert refreshed_donor.consumed_at is not None
        assert donor_detail is not None
        assert donor_detail["source_liquid_culture_id"] == liquid_culture.liquid_culture_id
        child_rows = {row["bag_ref"]: row for row in donor_detail["child_bags"]}
        assert set(child_rows) == {bag.bag_code for bag in child_bags}
        assert all(row["generation"] == 1 for row in child_rows.values())
        assert all(row["bag_type"] == "SPAWN" for row in child_rows.values())
    finally:
        db.close()


def test_substrate_inoculation_batch_assigns_codes_and_consumes_spawn():
    db = _session()
    try:
        _, _, spawn_bag, _ = _prepare_ready_spawn(db)
        substrate_recipe = _seed_substrate_recipe(db)
        fill_profile = _seed_fill_profile(db)
        mix_lot = _seed_mix_lot(db, substrate_recipe, fill_profile)
        pasteurization_run = _seed_pasteurization_run(db, mix_lot, substrate_recipe)

        unlabeled_bags = crud.create_substrate_bags(db, pasteurization_run.pasteurization_run_id, 3)
        inoculated_bags = crud.create_inoculation_batch(
            db,
            pasteurization_run.pasteurization_run_id,
            3,
            spawn_bag.bag_code,
        )
        consumed_spawn = crud.get_bag(db, spawn_bag.bag_code)

        assert [bag.bag_id for bag in unlabeled_bags] == ["SUBREC-0001", "SUBREC-0002", "SUBREC-0003"]
        assert [bag.bag_code for bag in inoculated_bags] == [
            "PAST-PAST-001-MM-LM-0001",
            "PAST-PAST-001-MM-LM-0002",
            "PAST-PAST-001-MM-LM-0003",
        ]
        assert all(bag.parent_spawn_bag_id == spawn_bag.bag_id for bag in inoculated_bags)
        assert all(bag.species_id == spawn_bag.species_id for bag in inoculated_bags)
        assert all(bag.status == "INOCULATED" for bag in inoculated_bags)
        assert consumed_spawn is not None
        assert consumed_spawn.consumed_at is not None
        assert consumed_spawn.status == "CONSUMED"
        assert len(crud.list_substrate_bags_inoculated_by(db, spawn_bag.bag_code)) == 3
    finally:
        db.close()


def test_single_inoculation_returns_inoculation_row_for_bag_refs():
    db = _session()
    try:
        _, _, spawn_bag, _ = _prepare_ready_spawn(db)
        substrate_recipe = _seed_substrate_recipe(db)
        fill_profile = _seed_fill_profile(db)
        mix_lot = _seed_mix_lot(db, substrate_recipe, fill_profile)
        pasteurization_run = _seed_pasteurization_run(db, mix_lot, substrate_recipe)
        substrate_bag = crud.create_substrate_bags(db, pasteurization_run.pasteurization_run_id, 1)[0]

        inoculation = crud.create_inoculation(db, substrate_bag.bag_id, spawn_bag.bag_code)
        refreshed_bag = crud.get_bag(db, substrate_bag.bag_id)

        assert inoculation.substrate_bag_id == substrate_bag.bag_id
        assert inoculation.spawn_bag_id == spawn_bag.bag_id
        assert refreshed_bag is not None
        assert refreshed_bag.bag_code == "PAST-PAST-001-MM-LM-0001"
        assert refreshed_bag.parent_spawn_bag_id == spawn_bag.bag_id
    finally:
        db.close()


def test_lifecycle_updates_and_harvests_work_with_printable_bag_codes():
    db = _session()
    try:
        _, _, _, substrate_bag = _prepare_inoculated_substrate(db)
        bag_code = substrate_bag.bag_code

        bag = crud.update_bag_incubation_start(db, bag_code)
        assert bag is not None
        assert bag.status == "INCUBATING"

        bag = crud.update_bag_ready(db, bag_code)
        assert bag is not None
        assert bag.status == "READY"

        bag = crud.update_bag_fruiting_start(db, bag_code)
        assert bag is not None
        assert bag.status == "FRUITING"

        harvest_1 = crud.create_harvest_event(db, bag_code, 1, 0.55)
        assert harvest_1.flush_number == 1
        assert crud.get_bag(db, bag_code).status == "FLUSH_1_COMPLETE"

        harvest_2 = crud.create_harvest_event(db, bag_code, 2, 0.35)
        assert harvest_2.flush_number == 2

        bag_detail = crud.get_bag_detail(db, bag_code)
        bag_by_internal_id = crud.get_bag(db, substrate_bag.bag_id)

        assert bag_detail is not None
        assert bag_detail["bag_code"] == bag_code
        assert bag_detail["status"] == "FLUSH_2_COMPLETE"
        assert len(bag_detail["harvest_events"]) == 2
        assert bag_by_internal_id is not None
        assert bag_by_internal_id.bag_code == bag_code
        assert crud.get_bag_total_harvest_kg(db, bag_code) == pytest.approx(0.9)
    finally:
        db.close()


def test_duplicate_flush_and_contamination_disposal_guardrails_use_bag_refs():
    db = _session()
    try:
        _, _, _, substrate_bag = _prepare_inoculated_substrate(db)
        bag_code = substrate_bag.bag_code

        crud.update_bag_incubation_start(db, bag_code)
        crud.update_bag_ready(db, bag_code)
        crud.update_bag_fruiting_start(db, bag_code)
        crud.create_harvest_event(db, bag_code, 1, 0.4)

        with pytest.raises(IntegrityError):
            crud.create_harvest_event(db, bag_code, 1, 0.3)

        contaminated_bag = crud.update_bag_disposal(db, bag_code, "CONTAMINATION")
        assert contaminated_bag is not None
        assert contaminated_bag.status == "CONTAMINATED"
        assert contaminated_bag.disposal_reason == "CONTAMINATION"
    finally:
        db.close()


def test_run_bag_creation_guardrails_prevent_overfilling_planned_counts():
    db = _session()
    try:
        spawn_recipe = _seed_spawn_recipe(db)
        grain_type = _seed_grain_type(db)
        sterilization_run = models.SterilizationRun(
            run_code="STER-LIMIT",
            spawn_recipe_id=spawn_recipe.spawn_recipe_id,
            grain_type_id=grain_type.grain_type_id,
            unloaded_at=datetime.now(timezone.utc),
            bag_count=2,
        )
        db.add(sterilization_run)

        substrate_recipe = _seed_substrate_recipe(db, recipe_code="MM-LIMIT")
        fill_profile = _seed_fill_profile(db)
        mix_lot = models.MixLot(
            lot_code="LOT-LIMIT",
            substrate_recipe_version_id=substrate_recipe.substrate_recipe_version_id,
            fill_profile_id=fill_profile.fill_profile_id,
        )
        db.add(mix_lot)
        db.commit()
        db.refresh(sterilization_run)
        db.refresh(mix_lot)

        pasteurization_run = models.PasteurizationRun(
            run_code="PAST-LIMIT",
            mix_lot_id=mix_lot.mix_lot_id,
            substrate_recipe_version_id=substrate_recipe.substrate_recipe_version_id,
            unloaded_at=datetime.now(timezone.utc),
            bag_count=2,
        )
        db.add(pasteurization_run)
        db.commit()
        db.refresh(pasteurization_run)

        crud.create_spawn_bags(db, sterilization_run.sterilization_run_id, 2)
        crud.create_substrate_bags(db, pasteurization_run.pasteurization_run_id, 2)

        with pytest.raises(ValueError, match="planned for 2 bag\\(s\\)"):
            crud.create_spawn_bags(db, sterilization_run.sterilization_run_id, 1)

        with pytest.raises(ValueError, match="planned for 2 bag\\(s\\)"):
            crud.create_substrate_bags(db, pasteurization_run.pasteurization_run_id, 1)
    finally:
        db.close()


def test_final_harvest_disposal_requires_harvested_substrate_bags():
    db = _session()
    try:
        _, spawn_bag, _, substrate_bag = _prepare_inoculated_substrate(db)

        with pytest.raises(ValueError, match="Only substrate bags can be disposed as FINAL_HARVEST"):
            crud.update_bag_disposal(db, spawn_bag.bag_code, "FINAL_HARVEST")

        with pytest.raises(ValueError, match="requires at least one recorded harvest"):
            crud.update_bag_disposal(db, substrate_bag.bag_code, "FINAL_HARVEST")

        crud.update_bag_incubation_start(db, substrate_bag.bag_code)
        crud.update_bag_ready(db, substrate_bag.bag_code)
        crud.update_bag_fruiting_start(db, substrate_bag.bag_code)
        crud.create_harvest_event(db, substrate_bag.bag_code, 1, 0.5)

        disposed_bag = crud.update_bag_disposal(db, substrate_bag.bag_code, "FINAL_HARVEST")

        assert disposed_bag is not None
        assert disposed_bag.status == "DISPOSED"
        assert disposed_bag.disposal_reason == "FINAL_HARVEST"
    finally:
        db.close()
