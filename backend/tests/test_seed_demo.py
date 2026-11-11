"""The demo data generator (lead developer brief, section 7).

The generator keeps its own books (`result.ledger`) of what it decided for
every bag. The report tests here add those books up without touching the
reporting code and compare the totals with what the reports say, so a fault
in either shows as a disagreement.
"""

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi.testclient import TestClient

from app import clock, models, seed_demo
from app.config import settings
from app.db import get_db
from app.main import app
from app.seed_demo import DemoConfig, DemoDataRefused

from .conftest import ADMIN_EMAIL, ORIGIN, make_user, sign_in

END = date(2026, 11, 10)
FARM = DemoConfig(seed=3, scale=1, weeks=9, end_date=END)
TINY = DemoConfig(seed=3, scale=0.5, weeks=2, end_date=END)
REPO = Path(__file__).resolve().parents[2]


def _new_database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    models.Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _fingerprint(db) -> str:
    """Everything the generator wrote that an operator could see, as one digest."""
    def stamp(value):
        return value.isoformat() if value is not None else None

    farm = {
        "sterilization_runs": [
            (run.run_code, stamp(run.unloaded_at), run.bag_count)
            for run in db.execute(select(models.SterilizationRun).order_by(models.SterilizationRun.run_code)).scalars()
        ],
        "pasteurization_runs": [
            (run.run_code, stamp(run.unloaded_at), run.bag_count)
            for run in db.execute(select(models.PasteurizationRun).order_by(models.PasteurizationRun.run_code)).scalars()
        ],
        "lots": [
            (lot.lot_code, lot.vendor, lot.vendor_lot_number, stamp(lot.received_at), stamp(lot.used_up_at))
            for lot in db.execute(select(models.PurchasedSpawnLot).order_by(models.PurchasedSpawnLot.lot_code)).scalars()
        ],
        "bags": [
            (
                bag.bag_id,
                bag.bag_code,
                bag.status,
                bag.species.code if bag.species else None,
                bag.inoculation_source_type,
                sorted((event.event_type, stamp(event.occurred_at)) for event in bag.status_events),
                sorted((h.flush_number, float(h.fresh_weight_kg), stamp(h.harvested_at)) for h in bag.harvest_events),
            )
            for bag in db.execute(select(models.Bag).order_by(models.Bag.bag_id)).unique().scalars()
        ],
    }
    return hashlib.sha256(json.dumps(farm, sort_keys=True).encode()).hexdigest()


@pytest.fixture(scope="module")
def demo_farm():
    """One generated farm, and the production report on it read through the API.

    Shared by the read-only tests below: generating it takes some seconds.
    """
    Session = _new_database()
    db = Session()
    result = seed_demo.generate(db, FARM)

    def _get_db():
        db.info.pop("user_id", None)
        yield db

    make_user(db, ADMIN_EMAIL, "admin")
    app.dependency_overrides[get_db] = _get_db
    try:
        client = sign_in(TestClient(app, headers={"Origin": ORIGIN}), ADMIN_EMAIL)
        response = client.get("/api/reports/production")
        assert response.status_code == 200, response.text
        report = response.json()
        assert client.get("/api/dashboard/overview").status_code == 200
        assert client.get("/api/bags?limit=50").status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)
    yield db, result, report
    db.close()


# ---------------------------------------------------------------- repeatable

def test_the_same_seed_gives_the_same_farm_and_another_seed_a_different_one():
    def farm(config):
        db = _new_database()()
        try:
            seed_demo.generate(db, config)
            return _fingerprint(db)
        finally:
            db.close()

    config = DemoConfig(seed=11, scale=0.5, weeks=5, end_date=END)
    first = farm(config)
    assert farm(config) == first
    assert farm(DemoConfig(seed=12, scale=0.5, weeks=5, end_date=END)) != first


def test_scale_multiplies_the_number_of_runs():
    def runs(scale):
        db = _new_database()()
        try:
            result = seed_demo.generate(db, DemoConfig(seed=1, scale=scale, weeks=2, end_date=END))
            return result.counts["pasteurization_runs"], result.counts["sterilization_runs"]
        finally:
            db.close()

    assert runs(1) == (4, 1)
    assert runs(3) == (12, 3)


# ------------------------------------------------------------------ realistic

def test_the_farm_has_bags_at_every_stage_and_uses_every_source(demo_farm):
    db, result, _ = demo_farm
    bags = db.execute(select(models.Bag)).unique().scalars().all()
    statuses = {bag.status for bag in bags}
    assert {"PASTEURIZED", "INCUBATING", "READY", "FRUITING", "DISPOSED", "CONTAMINATED", "CONSUMED"} <= statuses
    assert {entry.source_type for entry in result.ledger.values()} == {"LIQUID_CULTURE", "PURCHASED_SPAWN", "SPAWN_BAG"}
    assert len({entry.species_code for entry in result.ledger.values()}) >= 4
    assert any(len(entry.harvests_kg) == 2 for entry in result.ledger.values())
    # Every label fits (SRS BAG-5).
    assert all(len(code) <= 18 for code in result.ledger)


def test_nothing_is_stamped_outside_the_story_and_each_bag_s_history_is_in_order(demo_farm):
    db, result, _ = demo_farm
    zone = ZoneInfo(settings.farm_timezone)
    start = datetime(result.first_day.year, result.first_day.month, result.first_day.day, tzinfo=zone)
    end = datetime(END.year, END.month, END.day, 18, 30, tzinfo=zone)
    order = ["CREATED", "BAG_CODE_ASSIGNED", "INOCULATED", "INCUBATION_STARTED", "READY", "FRUITING_STARTED"]

    def aware(value):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    for bag in db.execute(select(models.Bag)).unique().scalars():
        times = {}
        for event in bag.status_events:
            moment = aware(event.occurred_at)
            assert start <= moment <= end, (bag.bag_ref, event.event_type, moment)
            times.setdefault(event.event_type, moment)
        seen = [times[name] for name in order if name in times]
        assert seen == sorted(seen), bag.bag_ref
        if "DISPOSED" in times:
            assert times["DISPOSED"] >= max(times.values()), bag.bag_ref


def test_one_run_went_badly_and_the_rest_did_not(demo_farm):
    _, result, _ = demo_farm
    by_run = defaultdict(list)
    for entry in result.ledger.values():
        if entry.bag_type == "SUBSTRATE":
            by_run[entry.run_code].append(entry.contaminated)
    assert result.bad_run_code in by_run
    bad = by_run.pop(result.bad_run_code)
    assert sum(bad) / len(bad) > 0.25
    others = [flag for flags in by_run.values() for flag in flags]
    assert 0 < sum(others) / len(others) < 0.10


# ------------------------------------------- the reports against the ledger

@pytest.fixture
def report(demo_farm):
    _, result, body = demo_farm
    return result, body


def test_the_report_totals_equal_the_generator_s_own_books(report):
    result, body = report
    summary = body["summary"]
    ledger = result.ledger.values()
    substrate = [entry for entry in ledger if entry.bag_type == "SUBSTRATE"]

    harvest_kg = sum(sum(entry.harvests_kg) for entry in substrate)
    dry_kg = result.fill_dry_kg * result.counts["substrate_bag_records"]
    contaminated = sum(1 for entry in ledger if entry.contaminated)

    assert summary["total_spawn_bags"] == result.counts["spawn_bag_records"]
    assert summary["total_substrate_bags"] == result.counts["substrate_bag_records"]
    assert summary["total_contaminated_bags"] == contaminated
    assert summary["contamination_rate"] == pytest.approx(contaminated / result.counts["bag_records"])
    assert summary["substrate_bags_with_harvest"] == sum(1 for entry in substrate if entry.harvests_kg)
    assert summary["total_harvest_kg"] == pytest.approx(harvest_kg)
    assert summary["total_dry_weight_kg"] == pytest.approx(dry_kg)
    assert summary["overall_bio_efficiency"] == pytest.approx(harvest_kg / dry_kg)
    assert body["data_quality_issues"] == []


def test_contamination_by_species_and_by_run_equal_the_books(report):
    result, body = report
    by_species = defaultdict(lambda: [0, 0])
    by_run = defaultdict(lambda: {"contaminated": 0, "harvest_kg": 0.0, "bags": 0})
    for entry in result.ledger.values():
        by_species[entry.species_code][0] += 1
        by_species[entry.species_code][1] += entry.contaminated
        if entry.bag_type == "SUBSTRATE":
            run = by_run[entry.run_code]
            run["bags"] += 1
            run["contaminated"] += entry.contaminated
            run["harvest_kg"] += sum(entry.harvests_kg)

    reported_species = {row["key"]: row for row in body["contamination_by_species"]}
    assert set(reported_species) == set(by_species)
    for code, (total, contaminated) in by_species.items():
        assert reported_species[code]["total_bags"] == total, code
        assert reported_species[code]["contaminated_bags"] == contaminated, code

    reported_runs = {row["run_code"]: row for row in body["pasteurization_runs"]}
    for run_code, books in by_run.items():
        row = reported_runs[run_code]
        assert row["contaminated_bags"] == books["contaminated"], run_code
        assert row["total_harvest_kg"] == pytest.approx(books["harvest_kg"]), run_code
        assert row["total_bags"] >= books["bags"]
        if row["total_dry_weight_kg"]:
            assert row["bio_efficiency"] == pytest.approx(books["harvest_kg"] / row["total_dry_weight_kg"]), run_code
    worst = max(reported_runs.values(), key=lambda row: row["contamination_rate"])
    assert worst["run_code"] == result.bad_run_code


def test_contamination_by_root_source_follows_the_line_back_through_the_farm_s_own_spawn(report):
    """A substrate bag made from one of our spawn bags belongs to that spawn bag's culture or lot."""
    result, body = report

    def root(entry):
        if entry.source_type == "SPAWN_BAG":
            return root(result.ledger[entry.source_code])
        return entry.source_type, entry.source_code

    books = {"LIQUID_CULTURE": defaultdict(lambda: [0, 0]), "PURCHASED_SPAWN": defaultdict(lambda: [0, 0])}
    for entry in result.ledger.values():
        kind, code = root(entry)
        books[kind][code][0] += 1
        books[kind][code][1] += entry.contaminated

    for kind, section in (
        ("LIQUID_CULTURE", "contamination_by_liquid_culture"),
        ("PURCHASED_SPAWN", "contamination_by_purchased_spawn_lot"),
    ):
        reported = {row["label"].split(" ")[0]: row for row in body[section]}
        assert set(reported) == set(books[kind]), section
        for code, (total, contaminated) in books[kind].items():
            assert reported[code]["total_bags"] == total, (section, code)
            assert reported[code]["contaminated_bags"] == contaminated, (section, code)


# ----------------------------------------------------------------------- safe

def test_it_refuses_a_database_that_already_holds_farm_records(db_session):
    species = models.MushroomSpecies(code="LM", name="Lion's Mane", slug="lion-s-mane", is_active=True)
    db_session.add(species)
    db_session.flush()
    db_session.add(models.LiquidCulture(culture_code="LC-REAL", species_id=species.species_id, is_active=True))
    db_session.commit()

    with pytest.raises(DemoDataRefused, match="already holds 1 liquid cultures"):
        seed_demo.generate(db_session, TINY)
    assert db_session.execute(select(models.Bag)).first() is None

    result = seed_demo.generate(db_session, TINY, allow_existing_data=True)
    assert result.counts["bag_records"] > 0


def test_it_refuses_production_without_its_own_flag(db_session, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    with pytest.raises(DemoDataRefused, match="production"):
        seed_demo.generate(db_session, TINY)
    # The flag for existing data is a different permission.
    with pytest.raises(DemoDataRefused, match="production"):
        seed_demo.generate(db_session, TINY, allow_existing_data=True)
    assert seed_demo.generate(db_session, TINY, allow_production=True).counts["bag_records"] > 0


def test_nothing_that_runs_on_the_server_calls_the_generator():
    """Brief, section 7: never in the deploy workflow."""
    for name in (
        ".github/workflows/deploy-droplet.yml",
        "docker-compose.yml",
        "backend/Dockerfile",
        "ops/backup/backup.sh",
    ):
        assert "seed_demo" not in (REPO / name).read_text(encoding="utf-8"), name


def test_a_scale_or_length_out_of_range_is_refused(db_session):
    for config in (DemoConfig(scale=0), DemoConfig(scale=51), DemoConfig(weeks=0)):
        with pytest.raises(ValueError):
            seed_demo.generate(db_session, config)


# --------------------------------------------------------------- command line

def test_the_command_prints_what_it_made_and_refuses_a_second_run(monkeypatch, capsys):
    monkeypatch.setattr(seed_demo, "SessionLocal", _new_database())
    arguments = ["--seed", "5", "--scale", "0.5", "--weeks", "2", "--end-date", "2026-11-10"]

    assert seed_demo.main(arguments) == 0
    printed = capsys.readouterr().out
    assert "Demo farm from 2026-10-28 to 2026-11-10 (seed 5, scale 0.5, 2 weeks)" in printed
    assert "pasteurization runs:   2" in printed

    assert seed_demo.main(arguments) == 2
    assert "Refused: The database already holds" in capsys.readouterr().err


def test_the_work_can_be_recorded_under_a_user(db_session, admin_user):
    seed_demo.generate(db_session, TINY, user_email=ADMIN_EMAIL)
    events = db_session.execute(select(models.BagStatusEvent)).scalars().all()
    assert events and all(event.recorded_by_user_id == admin_user.user_id for event in events)
    assert "user_id" not in db_session.info

    with pytest.raises(DemoDataRefused, match="No user"):
        seed_demo.generate(db_session, TINY, allow_existing_data=True, user_email="nobody@example.com")


# ---------------------------------------------------------------------- clock

def test_the_clock_is_real_time_outside_a_simulation_and_is_put_back_after_one():
    moment = datetime(2026, 9, 1, 14, 0, tzinfo=ZoneInfo("America/New_York"))
    with clock.simulated(lambda: moment):
        assert clock.now() == moment
        assert clock.now().utcoffset() == timedelta(0)
    assert abs(clock.now() - datetime.now(timezone.utc)) < timedelta(seconds=5)

    with clock.simulated(lambda: datetime(2026, 9, 1, 14, 0)):
        with pytest.raises(ValueError, match="offset"):
            clock.now()
