"""Purchased spawn lots as an inoculation source (SRS REF-11, INO-6, INO-7), through the API."""

from datetime import timedelta

import pytest

from .conftest import iso


@pytest.fixture
def lot(farm):
    """A lot of purchased Lion's Mane spawn, received yesterday."""
    return farm.post(
        "/api/purchased-spawn-lots",
        {
            "vendor": "North Spore",
            "vendor_lot_number": "NS-48213",
            "species_id": farm.species["species_id"],
            "grain_type_id": farm.grain_type["grain_type_id"],
            "received_at": "2026-11-05T15:00:00-05:00",
            "quantity": 4,
            "quantity_unit": "bags",
            "notes": "5 lb bags",
        },
    )


def _substrate_run_with_bags(farm, bag_count):
    run = farm.pasteurization_run(bag_count=bag_count)
    farm.post("/api/bags/substrate", {"pasteurization_run_id": run["pasteurization_run_id"], "bag_count": bag_count})
    return run


def _inoculate_from_lot(farm, run, lot, bag_count, **extra):
    return farm.post(
        "/api/inoculations/batch",
        {
            "pasteurization_run_id": run["pasteurization_run_id"],
            "purchased_spawn_lot_id": lot["purchased_spawn_lot_id"],
            "bag_count": bag_count,
            **extra,
        },
    )


# ---------------------------------------------------------------- REF-11

def test_a_lot_records_vendor_species_grain_date_and_quantity(farm, lot):
    assert lot == {
        "purchased_spawn_lot_id": lot["purchased_spawn_lot_id"],
        # The farm's own name for it: species and the day it arrived, at the farm.
        "lot_code": "PL-LM-261105A",
        "vendor": "North Spore",
        "vendor_lot_number": "NS-48213",
        "species_id": farm.species["species_id"],
        "species_code": "LM",
        "species_name": "Lion's Mane",
        "grain_type_id": farm.grain_type["grain_type_id"],
        "grain_type_name": "Rye",
        "received_at": "2026-11-05T20:00:00Z",
        "quantity": 4.0,
        "quantity_unit": "bags",
        "notes": "5 lb bags",
        "is_active": True,
        "is_used_up": False,
        "used_up_at": None,
        "created_at": lot["created_at"],
    }
    # A second lot of the same species on the same day takes the next letter.
    second = farm.post(
        "/api/purchased-spawn-lots",
        {"vendor": "Field & Forest", "species_id": farm.species["species_id"], "received_at": "2026-11-05T09:00:00-05:00"},
    )
    assert second["lot_code"] == "PL-LM-261105B"
    assert [row["lot_code"] for row in farm.get("/api/purchased-spawn-lots")] == ["PL-LM-261105A", "PL-LM-261105B"]


@pytest.mark.parametrize(
    "change, status",
    [
        ({"vendor": ""}, 422),
        ({"quantity": 0}, 422),
        ({"received_at": "2026-11-05T15:00:00"}, 422),  # no offset
        ({"species_id": 9999}, 404),
        ({"grain_type_id": 9999}, 404),
    ],
)
def test_a_lot_with_bad_details_is_refused(farm, change, status):
    body = {"vendor": "North Spore", "species_id": farm.species["species_id"], "received_at": iso(farm.now), **change}
    assert farm.client.post("/api/purchased-spawn-lots", json=body).status_code == status
    assert farm.get("/api/purchased-spawn-lots") == []


def test_a_lot_can_be_corrected_until_it_has_been_used(farm, lot):
    path = f"/api/purchased-spawn-lots/{lot['purchased_spawn_lot_id']}"
    blue = farm.post("/api/species", {"code": "BO", "name": "Blue Oyster"})

    edited = farm.client.patch(path, json={"vendor": "North Spore LLC", "quantity": 5, "species_id": blue["species_id"]})
    assert edited.status_code == 200
    assert (edited.json()["vendor"], edited.json()["quantity"], edited.json()["species_code"]) == ("North Spore LLC", 5.0, "BO")
    # The code was given when the lot was recorded and stays as it is.
    assert edited.json()["lot_code"] == "PL-LM-261105A"

    run = _substrate_run_with_bags(farm, 1)
    _inoculate_from_lot(farm, run, lot, 1)
    refused = farm.client.patch(path, json={"species_id": farm.species["species_id"]})
    assert refused.status_code == 400
    assert "already inoculated bags" in refused.json()["detail"]
    assert farm.client.patch("/api/purchased-spawn-lots/9999", json={"vendor": "x"}).status_code == 404


def test_an_operator_records_and_uses_lots(farm, lot, operator_client):
    work = farm.as_user(operator_client)
    mine = work.post(
        "/api/purchased-spawn-lots",
        {"vendor": "Mycelia", "species_id": farm.species["species_id"], "received_at": iso(farm.now)},
    )
    run = _substrate_run_with_bags(work, 1)
    bags = _inoculate_from_lot(work, run, mine, 1)
    assert bags[0]["source_purchased_spawn_lot_code"] == mine["lot_code"]


# ---------------------------------------------------------------- INO-6: substrate

def test_substrate_bags_are_inoculated_from_a_purchased_lot(farm, lot):
    run = _substrate_run_with_bags(farm, 3)
    bags = _inoculate_from_lot(farm, run, lot, 2, inoculated_at="2026-11-09T10:00:00-05:00", notes="first shelf")

    assert [bag["bag_code"] for bag in bags] == [f"SB-LM-{run['run_code']}-01", f"SB-LM-{run['run_code']}-02"]
    for bag in bags:
        assert bag["status"] == "INOCULATED"
        assert bag["species_id"] == farm.species["species_id"]  # takes the lot's species
        assert bag["inoculation_source_type"] == "PURCHASED_SPAWN"
        assert bag["source_purchased_spawn_lot_id"] == lot["purchased_spawn_lot_id"]
        assert bag["source_purchased_spawn_lot_code"] == "PL-LM-261105A"
        assert bag["parent_spawn_bag_id"] is None and bag["source_liquid_culture_id"] is None
        assert bag["inoculated_at"] == "2026-11-09T15:00:00Z"

    detail = farm.get(f"/api/bags/{bags[0]['bag_id']}")
    inoculated = next(e for e in detail["status_events"] if e["event_type"] == "INOCULATED")
    assert inoculated["detail"] == "Inoculated from purchased spawn lot PL-LM-261105A (North Spore)"
    assert inoculated["notes"] == "first shelf"
    assert inoculated["recorded_by_name"] == "Ada Admin"

    # The whole life of a bag works from here exactly as it does from a spawn bag.
    first = bags[0]["bag_id"]
    farm.post(f"/api/bags/{first}/incubation-start")
    farm.post(f"/api/bags/{first}/ready")
    farm.post(f"/api/bags/{first}/fruiting-start")
    farm.post("/api/harvest-events", {"bag_id": first, "flush_number": 1, "fresh_weight_kg": 0.6})
    assert farm.get(f"/api/bags/{first}")["bio_efficiency"] == pytest.approx(0.6)


def test_a_lot_serves_many_sessions_until_it_is_marked_used_up(farm, lot):
    """INO-7: unlike one of the farm's own spawn bags, a lot is not consumed by its first session."""
    path = f"/api/purchased-spawn-lots/{lot['purchased_spawn_lot_id']}"
    first_run = _substrate_run_with_bags(farm, 2)
    second_run = _substrate_run_with_bags(farm, 2)

    _inoculate_from_lot(farm, first_run, lot, 2)
    _inoculate_from_lot(farm, second_run, lot, 1)
    assert farm.get("/api/purchased-spawn-lots?usable_only=true")[0]["is_used_up"] is False

    used = farm.client.patch(path, json={"used_up": True}).json()
    assert used["is_used_up"] is True and used["used_up_at"] is not None
    assert farm.get("/api/purchased-spawn-lots?usable_only=true") == []
    assert len(farm.get("/api/purchased-spawn-lots")) == 1  # still listed, for the record

    refused = farm.client.post(
        "/api/inoculations/batch",
        json={
            "pasteurization_run_id": second_run["pasteurization_run_id"],
            "purchased_spawn_lot_id": lot["purchased_spawn_lot_id"],
            "bag_count": 1,
        },
    )
    assert refused.status_code == 400
    assert refused.json()["detail"] == "Purchased spawn lot PL-LM-261105A is marked used up. Reopen it if some is left"

    # Marked by mistake: reopen it and carry on.
    assert farm.client.patch(path, json={"used_up": False}).json()["is_used_up"] is False
    assert len(_inoculate_from_lot(farm, second_run, lot, 1)) == 1


def test_a_deactivated_or_unknown_lot_cannot_inoculate(farm, lot):
    run = _substrate_run_with_bags(farm, 1)
    body = {"pasteurization_run_id": run["pasteurization_run_id"], "bag_count": 1}

    assert farm.client.post("/api/inoculations/batch", json={**body, "purchased_spawn_lot_id": 9999}).status_code == 404

    farm.client.patch(f"/api/purchased-spawn-lots/{lot['purchased_spawn_lot_id']}", json={"is_active": False})
    refused = farm.client.post(
        "/api/inoculations/batch", json={**body, "purchased_spawn_lot_id": lot["purchased_spawn_lot_id"]}
    )
    assert refused.status_code == 400 and "is deactivated" in refused.json()["detail"]
    assert farm.get("/api/bags?status=INOCULATED") == []


def test_a_session_names_exactly_one_source(farm, lot):
    run = _substrate_run_with_bags(farm, 1)
    body = {"pasteurization_run_id": run["pasteurization_run_id"], "bag_count": 1}
    neither = farm.client.post("/api/inoculations/batch", json=body)
    both = farm.client.post(
        "/api/inoculations/batch",
        json={**body, "spawn_bag_id": "SP-LM-261109A-01", "purchased_spawn_lot_id": lot["purchased_spawn_lot_id"]},
    )
    assert neither.status_code == both.status_code == 422
    assert "exactly one source" in neither.text


def test_a_bag_is_inoculated_only_once_whatever_the_source(farm, lot):
    run = _substrate_run_with_bags(farm, 1)
    bag = _inoculate_from_lot(farm, run, lot, 1)[0]
    spawn = farm.ready_spawn_bag()
    again = farm.client.post(
        "/api/inoculations", json={"substrate_bag_id": bag["bag_id"], "spawn_bag_id": spawn["bag_id"]}
    )
    assert again.status_code == 400
    assert "already inoculated" in again.json()["detail"]
    # The spawn bag was not consumed by the refused attempt.
    assert farm.get(f"/api/bags/{spawn['bag_id']}")["status"] == "READY"


# ---------------------------------------------------------------- INO-6: spawn bags

def test_spawn_bags_are_inoculated_from_a_purchased_lot_and_carry_it_down_the_line(farm, lot):
    spawn_run = farm.sterilization_run(bag_count=2)
    farm.post("/api/bags/spawn", {"sterilization_run_id": spawn_run["sterilization_run_id"], "bag_count": 2})
    spawn_bags = farm.post(
        "/api/spawn-inoculations/batch",
        {
            "sterilization_run_id": spawn_run["sterilization_run_id"],
            "source_type": "PURCHASED_SPAWN",
            "purchased_spawn_lot_id": lot["purchased_spawn_lot_id"],
            "bag_count": 2,
        },
    )
    assert [b["bag_code"] for b in spawn_bags] == [f"SP-LM-{spawn_run['run_code']}-01", f"SP-LM-{spawn_run['run_code']}-02"]
    assert all(b["inoculation_source_type"] == "PURCHASED_SPAWN" for b in spawn_bags)

    # One of them, once colonized, inoculates substrate: the lot is still the root of that line.
    source = spawn_bags[0]["bag_id"]
    farm.post(f"/api/bags/{source}/incubation-start")
    farm.post(f"/api/bags/{source}/ready")
    run = _substrate_run_with_bags(farm, 1)
    farm.post(
        "/api/inoculations/batch",
        {"pasteurization_run_id": run["pasteurization_run_id"], "spawn_bag_id": source, "bag_count": 1},
    )
    row = farm.get("/api/reports/production")["substrate_bags"][0]
    assert row["source_purchased_spawn_lot_code"] == "PL-LM-261105A"
    assert row["spawn_generation"] == 1  # through one generation of the farm's own spawn
    assert row["parent_spawn_bag_ref"] == spawn_bags[0]["bag_code"]


@pytest.mark.parametrize(
    "body",
    [
        {"source_type": "PURCHASED_SPAWN"},
        {"source_type": "PURCHASED_SPAWN", "purchased_spawn_lot_id": 1, "liquid_culture_id": 1},
        {"source_type": "LIQUID_CULTURE", "liquid_culture_id": 1, "purchased_spawn_lot_id": 1},
    ],
)
def test_spawn_inoculation_source_fields_must_match_the_source_type(farm, body):
    response = farm.client.post(
        "/api/spawn-inoculations/batch", json={"sterilization_run_id": 1, "bag_count": 1, **body}
    )
    assert response.status_code == 422


# ---------------------------------------------------------------- reports

def test_contamination_is_reported_by_purchased_lot_and_source_type(farm, lot):
    other = farm.post(
        "/api/purchased-spawn-lots",
        {"vendor": "Field & Forest", "species_id": farm.species["species_id"], "received_at": iso(farm.now - timedelta(days=2))},
    )
    run = _substrate_run_with_bags(farm, 5)
    from_first = _inoculate_from_lot(farm, run, lot, 3)
    _inoculate_from_lot(farm, run, other, 2)
    farm.post(f"/api/bags/{from_first[0]['bag_id']}/disposal", {"disposal_reason": "CONTAMINATION"})

    report = farm.get("/api/reports/production")
    by_lot = {row["label"]: row for row in report["contamination_by_purchased_spawn_lot"]}
    assert by_lot["PL-LM-261105A"]["total_bags"] == 3
    assert by_lot["PL-LM-261105A"]["contaminated_bags"] == 1
    assert by_lot["PL-LM-261105A"]["contamination_rate"] == pytest.approx(1 / 3)
    assert by_lot[other["lot_code"]]["contaminated_bags"] == 0

    by_source = {row["key"]: row for row in report["contamination_by_inoculation_source_type"]}
    assert by_source["PURCHASED_SPAWN"]["label"] == "Purchased Spawn"
    assert by_source["PURCHASED_SPAWN"]["total_bags"] == 5

    by_generation = {row["key"]: row["label"] for row in report["contamination_by_spawn_generation"]}
    assert by_generation["0"] == "Straight from purchased spawn"

    # Nothing about a lot-sourced bag is reported as a data problem.
    assert report["data_quality_issues"] == []
