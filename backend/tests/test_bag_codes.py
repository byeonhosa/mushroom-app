"""Bag codes, run codes and internal IDs (SRS BAG-5, RUN-6, BAG-11), through the API."""

from datetime import date, datetime, timezone

import pytest

from app import bag_id, models

from .conftest import iso


def _spawn_bags(farm, run, count, **source):
    farm.post("/api/bags/spawn", {"sterilization_run_id": run["sterilization_run_id"], "bag_count": count})
    return farm.post(
        "/api/spawn-inoculations/batch",
        {
            "sterilization_run_id": run["sterilization_run_id"],
            "source_type": "LIQUID_CULTURE",
            "liquid_culture_id": farm.liquid_culture["liquid_culture_id"],
            "bag_count": count,
            **source,
        },
    )


# ---------------------------------------------------------------- RUN-6

def test_next_run_code_is_the_date_and_the_first_free_letter(farm):
    assert farm.get("/api/sterilization-runs/next-code?on=2026-11-09") == {
        "run_code": "261109A",
        "run_date": "2026-11-09",
    }
    farm.sterilization_run(run_code="261109A")
    assert farm.next_code("sterilization", on="2026-11-09") == "261109B"

    # A gap is filled before the next letter is taken.
    farm.sterilization_run(run_code="261109C")
    assert farm.next_code("sterilization", on="2026-11-09") == "261109B"
    farm.sterilization_run(run_code="261109B")
    assert farm.next_code("sterilization", on="2026-11-09") == "261109D"

    # Another day starts again at A, and pasteurization runs have their own letters.
    assert farm.next_code("sterilization", on="2026-11-10") == "261110A"
    assert farm.next_code("pasteurization", on="2026-11-09") == "261109A"


def test_next_run_code_defaults_to_today_at_the_farm(farm, monkeypatch):
    # 02:30 UTC on November 10 is still the evening of November 9 in Virginia.
    class _Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 10, 2, 30, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(bag_id, "datetime", _Clock)
    assert bag_id.farm_today() == date(2026, 11, 9)
    assert farm.get("/api/pasteurization-runs/next-code") == {"run_code": "261109A", "run_date": "2026-11-09"}


def test_next_run_code_route_is_not_mistaken_for_a_run_id(farm):
    assert farm.client.get("/api/sterilization-runs/next-code").status_code == 200
    assert farm.client.get("/api/pasteurization-runs/next-code").status_code == 200
    assert farm.client.get("/api/sterilization-runs/next-code?on=not-a-date").status_code == 422


@pytest.mark.parametrize("run_code", ["STER-20261109-001", "261109", "261109AA", "2611A", "", "26110901"])
def test_a_run_code_outside_the_format_is_refused_with_an_example(farm, run_code):
    response = farm.client.post(
        "/api/pasteurization-runs",
        json={
            "run_code": run_code,
            "mix_lot_id": farm.mix_lot["mix_lot_id"],
            "substrate_recipe_version_id": farm.substrate_recipe_id,
            "unloaded_at": iso(farm.now),
            "bag_count": 2,
        },
    )
    assert response.status_code == 422
    assert "261109A" in response.text


def test_a_run_code_is_stored_trimmed_and_in_capitals(farm):
    assert farm.sterilization_run(run_code=" 261109a ")["run_code"] == "261109A"


# ---------------------------------------------------------------- BAG-5

def test_spawn_and_substrate_bag_codes_follow_the_short_format(farm):
    spawn_run = farm.sterilization_run(run_code="261109A", bag_count=3)
    spawn_bags = _spawn_bags(farm, spawn_run, 3)
    assert [bag["bag_code"] for bag in spawn_bags] == ["SP-LM-261109A-01", "SP-LM-261109A-02", "SP-LM-261109A-03"]

    source = spawn_bags[0]["bag_id"]
    farm.post(f"/api/bags/{source}/incubation-start")
    farm.post(f"/api/bags/{source}/ready")

    substrate_run = farm.pasteurization_run(run_code="261109A", bag_count=2)
    farm.post("/api/bags/substrate", {"pasteurization_run_id": substrate_run["pasteurization_run_id"], "bag_count": 2})
    substrate_bags = farm.post(
        "/api/inoculations/batch",
        {"spawn_bag_id": source, "pasteurization_run_id": substrate_run["pasteurization_run_id"], "bag_count": 2},
    )
    # Same run code as the sterilization run: the SB prefix keeps the codes apart.
    assert [bag["bag_code"] for bag in substrate_bags] == ["SB-LM-261109A-01", "SB-LM-261109A-02"]

    for bag in spawn_bags + substrate_bags:
        assert len(bag["bag_code"]) <= bag_id.BAG_CODE_MAX_LENGTH
        # Either identifier finds the bag (BAG-6).
        assert farm.get(f"/api/bags/{bag['bag_code']}")["bag_id"] == bag["bag_id"]


def test_bag_numbers_run_on_through_a_run_across_sessions_and_species(farm):
    farm.post("/api/species", {"code": "BO", "name": "Blue Oyster"})
    blue_oyster = next(s for s in farm.get("/api/species") if s["code"] == "BO")
    blue_culture = farm.post(
        "/api/liquid-cultures", {"culture_code": "LC-BO-1", "species_id": blue_oyster["species_id"]}
    )

    run = farm.sterilization_run(run_code="261109A", bag_count=6)
    farm.post("/api/bags/spawn", {"sterilization_run_id": run["sterilization_run_id"], "bag_count": 6})

    def inoculate(count, culture):
        return [
            bag["bag_code"]
            for bag in farm.post(
                "/api/spawn-inoculations/batch",
                {
                    "sterilization_run_id": run["sterilization_run_id"],
                    "source_type": "LIQUID_CULTURE",
                    "liquid_culture_id": culture["liquid_culture_id"],
                    "bag_count": count,
                },
            )
        ]

    first = inoculate(2, farm.liquid_culture)
    second = inoculate(3, blue_culture)
    third = inoculate(1, farm.liquid_culture)

    # The number is the bag's place in the run, whatever went into it.
    assert first == ["SP-LM-261109A-01", "SP-LM-261109A-02"]
    assert second == ["SP-BO-261109A-03", "SP-BO-261109A-04", "SP-BO-261109A-05"]
    assert third == ["SP-LM-261109A-06"]
    assert len(set(first + second + third)) == 6


def test_the_longest_possible_bag_code_is_eighteen_characters(farm):
    farm.post("/api/species", {"code": "BKO", "name": "Black King Oyster"})
    black_king = next(s for s in farm.get("/api/species") if s["code"] == "BKO")
    culture = farm.post("/api/liquid-cultures", {"culture_code": "LC-BKO-1", "species_id": black_king["species_id"]})

    # 999 is the largest run the API accepts, and three characters the longest species code.
    run = farm.sterilization_run(run_code="261109Z", bag_count=999)
    bags = _spawn_bags(farm, run, 2, liquid_culture_id=culture["liquid_culture_id"])
    assert [bag["bag_code"] for bag in bags] == ["SP-BKO-261109Z-001", "SP-BKO-261109Z-002"]
    assert len(bags[0]["bag_code"]) == bag_id.BAG_CODE_MAX_LENGTH


def test_a_run_from_before_the_standard_gets_a_code_without_the_repeated_prefix(db_session, farm):
    """Existing run codes are not rewritten; their bags no longer read STER-STER-..."""
    run = models.SterilizationRun(
        run_code="STER-20260601-001",
        spawn_recipe_id=farm.spawn_recipe_id,
        grain_type_id=farm.grain_type["grain_type_id"],
        unloaded_at=farm.now,
        bag_count=2,
    )
    db_session.add(run)
    db_session.commit()

    bags = _spawn_bags(farm, {"sterilization_run_id": run.sterilization_run_id}, 2)
    assert [bag["bag_code"] for bag in bags] == ["SP-LM-STER-20260601-001-01", "SP-LM-STER-20260601-001-02"]


@pytest.mark.parametrize("code", ["lions_mane", "L", "LMXX", "L-M", ""])
def test_a_species_code_that_would_not_fit_the_label_is_refused(farm, code):
    response = farm.client.post("/api/species", json={"code": code, "name": "Too Long"})
    assert response.status_code == 422
    assert "two or three" in response.text


def test_a_species_code_is_stored_in_capitals(farm):
    assert farm.post("/api/species", {"code": " ko ", "name": "King Oyster"})["code"] == "KO"
    species_id = next(s for s in farm.get("/api/species") if s["code"] == "KO")["species_id"]
    updated = farm.client.patch(f"/api/species/{species_id}", json={"code": "kt"})
    assert updated.status_code == 200 and updated.json()["code"] == "KT"


# ---------------------------------------------------------------- BAG-11

def test_internal_ids_come_from_a_counter_and_never_repeat(db_session, farm):
    run_a = farm.sterilization_run(bag_count=3)
    run_b = farm.pasteurization_run(bag_count=3)
    run_c = farm.sterilization_run(bag_count=3)

    first = farm.post("/api/bags/spawn", {"sterilization_run_id": run_a["sterilization_run_id"], "bag_count": 2})
    substrate = farm.post("/api/bags/substrate", {"pasteurization_run_id": run_b["pasteurization_run_id"], "bag_count": 3})
    second = farm.post("/api/bags/spawn", {"sterilization_run_id": run_c["sterilization_run_id"], "bag_count": 2})
    third = farm.post("/api/bags/spawn", {"sterilization_run_id": run_a["sterilization_run_id"], "bag_count": 1})

    assert [b["bag_id"] for b in first] == ["SPNREC-0001", "SPNREC-0002"]
    assert [b["bag_id"] for b in second] == ["SPNREC-0003", "SPNREC-0004"]
    assert [b["bag_id"] for b in third] == ["SPNREC-0005"]
    assert [b["bag_id"] for b in substrate] == ["SUBREC-0001", "SUBREC-0002", "SUBREC-0003"]

    counters = {row.name: row.next_value for row in db_session.query(models.IdCounter).all()}
    assert counters == {"SPNREC": 6, "SUBREC": 4}


def test_a_refused_request_does_not_use_up_numbers(db_session, farm):
    run = farm.sterilization_run(bag_count=2)
    farm.post("/api/bags/spawn", {"sterilization_run_id": run["sterilization_run_id"], "bag_count": 1})
    # Over the planned count: refused before any number is taken.
    refused = farm.client.post(
        "/api/bags/spawn", json={"sterilization_run_id": run["sterilization_run_id"], "bag_count": 5}
    )
    assert refused.status_code == 400
    again = farm.post("/api/bags/spawn", {"sterilization_run_id": run["sterilization_run_id"], "bag_count": 1})
    assert again[0]["bag_id"] == "SPNREC-0002"


def test_a_missing_counter_row_starts_after_the_highest_id_in_use(db_session, farm):
    """A database that predates the counter table picks up where the IDs left off."""
    run = farm.sterilization_run(bag_count=5)
    farm.post("/api/bags/spawn", {"sterilization_run_id": run["sterilization_run_id"], "bag_count": 3})
    db_session.query(models.IdCounter).delete()
    db_session.commit()

    more = farm.post("/api/bags/spawn", {"sterilization_run_id": run["sterilization_run_id"], "bag_count": 2})
    assert [b["bag_id"] for b in more] == ["SPNREC-0004", "SPNREC-0005"]
