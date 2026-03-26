"""Tests for the operator dashboard overview."""

from datetime import datetime, timezone

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


def _seed_species(db, *, code: str, name: str):
    row = models.MushroomSpecies(code=code, name=name, is_active=True)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_liquid_culture(db, species, *, culture_code: str):
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


def _seed_substrate_recipe(db, *, name: str, recipe_code: str):
    row = models.SubstrateRecipeVersion(name=name, recipe_code=recipe_code, notes="")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_spawn_recipe(db, *, recipe_code: str):
    row = models.SpawnRecipe(recipe_code=recipe_code, notes="")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_fill_profile(db, *, name: str, target_dry_kg_per_bag: float = 1.0):
    row = models.FillProfile(
        name=name,
        target_dry_kg_per_bag=target_dry_kg_per_bag,
        target_water_kg_per_bag=1.25,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_grain_type(db, *, name: str):
    row = models.GrainType(name=name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_mix_lot(db, substrate_recipe, fill_profile, *, lot_code: str):
    row = models.MixLot(
        lot_code=lot_code,
        substrate_recipe_version_id=substrate_recipe.substrate_recipe_version_id,
        fill_profile_id=fill_profile.fill_profile_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_pasteurization_run(db, mix_lot, substrate_recipe, *, run_code: str, bag_count: int):
    row = models.PasteurizationRun(
        run_code=run_code,
        mix_lot_id=mix_lot.mix_lot_id,
        substrate_recipe_version_id=substrate_recipe.substrate_recipe_version_id,
        unloaded_at=datetime.now(timezone.utc),
        bag_count=bag_count,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _seed_sterilization_run(db, spawn_recipe, grain_type, *, run_code: str, bag_count: int):
    row = models.SterilizationRun(
        run_code=run_code,
        spawn_recipe_id=spawn_recipe.spawn_recipe_id,
        grain_type_id=grain_type.grain_type_id,
        unloaded_at=datetime.now(timezone.utc),
        bag_count=bag_count,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _prepare_ready_spawn(
    db,
    *,
    species_code: str,
    species_name: str,
    culture_code: str,
    spawn_recipe_code: str,
    grain_name: str,
    run_code: str,
):
    species = _seed_species(db, code=species_code, name=species_name)
    liquid_culture = _seed_liquid_culture(db, species, culture_code=culture_code)
    spawn_recipe = _seed_spawn_recipe(db, recipe_code=spawn_recipe_code)
    grain_type = _seed_grain_type(db, name=grain_name)
    sterilization_run = _seed_sterilization_run(
        db,
        spawn_recipe,
        grain_type,
        run_code=run_code,
        bag_count=1,
    )
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


def test_dashboard_overview_summarizes_operator_queues_and_run_worklists():
    db = _session()
    try:
        _, _, source_spawn = _prepare_ready_spawn(
            db,
            species_code="LM",
            species_name="Lion's Mane",
            culture_code="LC-LM-001",
            spawn_recipe_code="SR1",
            grain_name="Rye",
            run_code="STER-SOURCE",
        )
        _, ready_run, _ = _prepare_ready_spawn(
            db,
            species_code="BO",
            species_name="Blue Oyster",
            culture_code="LC-BO-001",
            spawn_recipe_code="SR2",
            grain_name="Millet",
            run_code="STER-READY",
        )

        open_spawn_recipe = _seed_spawn_recipe(db, recipe_code="SR3")
        open_grain_type = _seed_grain_type(db, name="Wheat")
        open_sterilization_run = _seed_sterilization_run(
            db,
            open_spawn_recipe,
            open_grain_type,
            run_code="STER-OPEN",
            bag_count=3,
        )
        crud.create_spawn_bags(db, open_sterilization_run.sterilization_run_id, 2)

        substrate_recipe = _seed_substrate_recipe(db, name="Masters Mix", recipe_code="MM")
        fill_profile = _seed_fill_profile(db, name="Dashboard Profile")

        open_mix_lot = _seed_mix_lot(db, substrate_recipe, fill_profile, lot_code="LOT-OPEN")
        open_pasteurization_run = _seed_pasteurization_run(
            db,
            open_mix_lot,
            substrate_recipe,
            run_code="PAST-OPEN",
            bag_count=1,
        )
        crud.create_substrate_bags(db, open_pasteurization_run.pasteurization_run_id, 1)

        active_mix_lot = _seed_mix_lot(db, substrate_recipe, fill_profile, lot_code="LOT-ACTIVE")
        active_pasteurization_run = _seed_pasteurization_run(
            db,
            active_mix_lot,
            substrate_recipe,
            run_code="PAST-ACTIVE",
            bag_count=5,
        )
        crud.create_substrate_bags(db, active_pasteurization_run.pasteurization_run_id, 5)
        (
            incubating_bag,
            ready_bag,
            fruiting_bag,
            second_flush_bag,
            contaminated_bag,
        ) = crud.create_inoculation_batch(
            db,
            active_pasteurization_run.pasteurization_run_id,
            5,
            source_spawn.bag_code,
        )

        for bag in (incubating_bag, ready_bag, fruiting_bag, second_flush_bag, contaminated_bag):
            crud.update_bag_incubation_start(db, bag.bag_code)

        for bag in (ready_bag, fruiting_bag, second_flush_bag):
            crud.update_bag_ready(db, bag.bag_code)

        crud.update_bag_fruiting_start(db, fruiting_bag.bag_code)
        crud.update_bag_fruiting_start(db, second_flush_bag.bag_code)
        crud.create_harvest_event(db, second_flush_bag.bag_code, 1, 0.45)
        crud.update_bag_disposal(db, contaminated_bag.bag_code, "CONTAMINATION")

        overview = crud.get_dashboard_overview(db)
        queues_by_key = {row["key"]: row for row in overview["queues"]}

        assert overview["summary"]["total_spawn_bags"] == 4
        assert overview["summary"]["total_substrate_bags"] == 6
        assert queues_by_key["spawn_unlabeled"]["count"] == 2
        assert queues_by_key["spawn_ready"]["count"] == 1
        assert queues_by_key["substrate_unlabeled"]["count"] == 1
        assert queues_by_key["substrate_incubating"]["count"] == 1
        assert queues_by_key["substrate_ready"]["count"] == 1
        assert queues_by_key["substrate_fruiting"]["count"] == 1
        assert queues_by_key["second_flush"]["count"] == 1
        assert queues_by_key["contaminated"]["count"] == 1
        assert queues_by_key["spawn_ready"]["href"] == "/bags?bag_type=SPAWN&status=READY"

        sterilization_rows = {row["run_code"]: row for row in overview["sterilization_runs"]}
        assert sterilization_rows["STER-OPEN"]["unlabeled_bags"] == 2
        assert sterilization_rows["STER-OPEN"]["next_action"] == "Create bag records"
        assert sterilization_rows["STER-READY"]["ready_bags"] == 1
        assert sterilization_rows["STER-READY"]["next_action"] == "Use ready spawn bags"
        assert sterilization_rows["STER-READY"]["href"] == f"/sterilization-runs/{ready_run.sterilization_run_id}"

        pasteurization_rows = {row["run_code"]: row for row in overview["pasteurization_runs"]}
        assert pasteurization_rows["PAST-OPEN"]["unlabeled_bags"] == 1
        assert pasteurization_rows["PAST-OPEN"]["next_action"] == "Inoculate unlabeled bags"
        assert pasteurization_rows["PAST-ACTIVE"]["ready_bags"] == 1
        assert pasteurization_rows["PAST-ACTIVE"]["fruiting_bags"] == 1
        assert pasteurization_rows["PAST-ACTIVE"]["contaminated_bags"] == 1
        assert pasteurization_rows["PAST-ACTIVE"]["harvested_bags"] == 1
        assert pasteurization_rows["PAST-ACTIVE"]["next_action"] == "Move ready bags to fruiting"
    finally:
        db.close()


def test_dashboard_overview_includes_alerts_and_recent_activity():
    db = _session()
    try:
        _, _, source_spawn = _prepare_ready_spawn(
            db,
            species_code="LM",
            species_name="Lion's Mane",
            culture_code="LC-LM-001",
            spawn_recipe_code="SR1",
            grain_name="Rye",
            run_code="STER-SOURCE",
        )
        substrate_recipe = _seed_substrate_recipe(db, name="Masters Mix", recipe_code="MM")
        fill_profile = _seed_fill_profile(db, name="Dashboard Alerts")
        mix_lot = _seed_mix_lot(db, substrate_recipe, fill_profile, lot_code="LOT-ALERTS")
        pasteurization_run = _seed_pasteurization_run(
            db,
            mix_lot,
            substrate_recipe,
            run_code="PAST-ALERTS",
            bag_count=1,
        )
        crud.create_substrate_bags(db, pasteurization_run.pasteurization_run_id, 1)
        contaminated_bag = crud.create_inoculation_batch(
            db,
            pasteurization_run.pasteurization_run_id,
            1,
            source_spawn.bag_code,
        )[0]
        crud.update_bag_incubation_start(db, contaminated_bag.bag_code)
        crud.update_bag_disposal(db, contaminated_bag.bag_code, "CONTAMINATION")

        bad_spawn = models.Bag(
            bag_id="SPNREC-BAD-0001",
            bag_type="SPAWN",
            sterilization_run_id=1,
            inoculated_at=datetime.now(timezone.utc),
            status="INOCULATED",
        )
        db.add(bad_spawn)
        db.commit()

        overview = crud.get_dashboard_overview(db)
        alert_titles = [row["title"] for row in overview["alerts"]]
        recent_activity = overview["recent_activity"]

        assert any("contamination case" in title.lower() for title in alert_titles)
        assert "Inoculated spawn bags missing an inoculation source" in alert_titles
        assert recent_activity[0]["event_type"] == "DISPOSED"
        assert recent_activity[0]["bag_ref"] == contaminated_bag.bag_code
        assert recent_activity[0]["title"] == "Disposed"
    finally:
        db.close()
