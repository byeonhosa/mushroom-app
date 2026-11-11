"""An administrator corrects a run after creating it (SRS RUN-5), through the API.

What can be corrected depends on what already rests on the run: its bags copy
its recipe when their records are created and print its code when labelled.
"""

from datetime import timedelta

import pytest

from .conftest import iso


def _patch(client, path, body, expect=200):
    response = client.patch(path, json=body)
    assert response.status_code == expect, f"PATCH {path} -> {response.status_code}: {response.text}"
    return response.json()


def test_the_details_of_a_sterilization_run_can_be_corrected(farm):
    run = farm.sterilization_run(run_code="261109A", bag_count=4)
    path = f"/api/sterilization-runs/{run['sterilization_run_id']}"
    unloaded = farm.now - timedelta(days=1)

    saved = _patch(
        farm.client,
        path,
        {
            "run_code": "261108A",
            "unloaded_at": iso(unloaded),
            "cycle_start_at": iso(unloaded - timedelta(hours=4)),
            "cycle_end_at": iso(unloaded - timedelta(hours=1)),
            "bag_count": 6,
            "temp_c": 121,
            "psi": 15,
            "hold_minutes": 150,
            "notes": "Entered a day late",
        },
    )
    assert saved["run_code"] == "261108A"
    assert saved["bag_count"] == 6
    assert (saved["temp_c"], saved["psi"], saved["hold_minutes"]) == (121, 15, 150)
    assert saved["notes"] == "Entered a day late"
    assert farm.get(path)["run_code"] == "261108A"

    # Only what is sent changes; a null for a required field leaves it.
    again = _patch(farm.client, path, {"notes": None, "run_code": None, "bag_count": None})
    assert (again["run_code"], again["bag_count"], again["notes"]) == ("261108A", 6, None)


def test_the_details_of_a_pasteurization_run_can_be_corrected(farm):
    run = farm.pasteurization_run(run_code="261109A", bag_count=10)
    path = f"/api/pasteurization-runs/{run['pasteurization_run_id']}"
    saved = _patch(farm.client, path, {"run_code": "261109B", "bag_count": 12, "notes": "Two extra bags"})
    assert (saved["run_code"], saved["bag_count"], saved["notes"]) == ("261109B", 12, "Two extra bags")


def test_the_run_code_is_fixed_once_a_label_carries_it(farm):
    run = farm.sterilization_run(run_code="261109A", bag_count=2)
    run_id = run["sterilization_run_id"]
    farm.post("/api/bags/spawn", {"sterilization_run_id": run_id, "bag_count": 2})

    # Records exist but no label yet: the code can still be corrected.
    assert _patch(farm.client, f"/api/sterilization-runs/{run_id}", {"run_code": "261108A"})["run_code"] == "261108A"

    bag = farm.post(
        "/api/spawn-inoculations/batch",
        {
            "sterilization_run_id": run_id,
            "source_type": "LIQUID_CULTURE",
            "liquid_culture_id": farm.liquid_culture["liquid_culture_id"],
            "bag_count": 1,
        },
    )[0]
    assert bag["bag_code"] == "SP-LM-261108A-01"

    refused = farm.client.patch(f"/api/sterilization-runs/{run_id}", json={"run_code": "261107A"})
    assert refused.status_code == 400
    assert "printed on 1 bag label" in refused.json()["detail"]
    # Sending the code it already has is not a change.
    _patch(farm.client, f"/api/sterilization-runs/{run_id}", {"run_code": "261108A", "notes": "ok"})


def test_the_recipe_is_fixed_once_bag_records_exist(farm):
    other_recipe = farm.post("/api/spawn-recipes", {"recipe_code": "MILLET-1"})
    other_grain = farm.post("/api/grain-types", {"name": "Millet"})
    run = farm.sterilization_run(bag_count=2)
    path = f"/api/sterilization-runs/{run['sterilization_run_id']}"

    saved = _patch(
        farm.client,
        path,
        {"spawn_recipe_id": other_recipe["spawn_recipe_id"], "grain_type_id": other_grain["grain_type_id"]},
    )
    assert saved["spawn_recipe_id"] == other_recipe["spawn_recipe_id"]

    farm.post("/api/bags/spawn", {"sterilization_run_id": run["sterilization_run_id"], "bag_count": 1})
    refused = farm.client.patch(path, json={"spawn_recipe_id": farm.spawn_recipe_id})
    assert refused.status_code == 400
    assert "already has 1 bag record" in refused.json()["detail"]

    substrate_run = farm.pasteurization_run(bag_count=2)
    farm.post("/api/bags/substrate", {"pasteurization_run_id": substrate_run["pasteurization_run_id"], "bag_count": 1})
    other = farm.post("/api/substrate-recipe-versions", {"name": "Hardwood", "recipe_code": "HW"})
    refused = farm.client.patch(
        f"/api/pasteurization-runs/{substrate_run['pasteurization_run_id']}",
        json={"substrate_recipe_version_id": other["substrate_recipe_version_id"]},
    )
    assert refused.status_code == 400


def test_a_run_cannot_be_moved_to_a_deactivated_or_missing_recipe(farm):
    retired = farm.post("/api/spawn-recipes", {"recipe_code": "OLD-1"})
    farm.client.patch(f"/api/spawn-recipes/{retired['spawn_recipe_id']}", json={"is_active": False})
    run = farm.sterilization_run()
    path = f"/api/sterilization-runs/{run['sterilization_run_id']}"
    assert farm.client.patch(path, json={"spawn_recipe_id": retired["spawn_recipe_id"]}).status_code == 400
    assert farm.client.patch(path, json={"spawn_recipe_id": 999}).status_code == 404
    assert farm.client.patch(path, json={"grain_type_id": 999}).status_code == 404


def test_the_planned_count_cannot_drop_below_the_records_that_exist(farm):
    run = farm.pasteurization_run(bag_count=5)
    run_id = run["pasteurization_run_id"]
    farm.post("/api/bags/substrate", {"pasteurization_run_id": run_id, "bag_count": 3})

    refused = farm.client.patch(f"/api/pasteurization-runs/{run_id}", json={"bag_count": 2})
    assert refused.status_code == 400
    assert "already has 3 bag record" in refused.json()["detail"]
    assert _patch(farm.client, f"/api/pasteurization-runs/{run_id}", {"bag_count": 3})["bag_count"] == 3
    # Raising it makes room for more records.
    _patch(farm.client, f"/api/pasteurization-runs/{run_id}", {"bag_count": 4})
    farm.post("/api/bags/substrate", {"pasteurization_run_id": run_id, "bag_count": 1})


def test_the_planned_count_cannot_cross_one_hundred_once_labels_exist(farm):
    """Bag numbers are printed with two digits under 100 bags and three from 100 (D-013)."""
    run = farm.sterilization_run(bag_count=50)
    run_id = run["sterilization_run_id"]
    path = f"/api/sterilization-runs/{run_id}"
    _patch(farm.client, path, {"bag_count": 120})
    _patch(farm.client, path, {"bag_count": 50})

    farm.post("/api/bags/spawn", {"sterilization_run_id": run_id, "bag_count": 1})
    farm.post(
        "/api/spawn-inoculations/batch",
        {
            "sterilization_run_id": run_id,
            "source_type": "LIQUID_CULTURE",
            "liquid_culture_id": farm.liquid_culture["liquid_culture_id"],
            "bag_count": 1,
        },
    )
    refused = farm.client.patch(path, json={"bag_count": 120})
    assert refused.status_code == 400
    assert "cannot cross 100" in refused.json()["detail"]
    _patch(farm.client, path, {"bag_count": 99})


def test_times_out_of_order_are_refused_against_what_the_run_already_holds(farm):
    run = farm.sterilization_run()
    path = f"/api/sterilization-runs/{run['sterilization_run_id']}"
    unloaded = farm.now - timedelta(hours=2)

    refused = farm.client.patch(path, json={"cycle_end_at": iso(unloaded + timedelta(hours=1))})
    assert refused.status_code == 400
    assert "unloaded before its cycle ends" in refused.json()["detail"]

    _patch(farm.client, path, {"cycle_start_at": iso(unloaded - timedelta(hours=3))})
    refused = farm.client.patch(path, json={"cycle_end_at": iso(unloaded - timedelta(hours=4))})
    assert refused.status_code == 400
    assert "end before it starts" in refused.json()["detail"]
    # The refused change was not half-applied.
    assert farm.get(path)["cycle_end_at"] is None

    assert farm.client.patch(path, json={"unloaded_at": "2026-11-09T10:00:00"}).status_code == 422


@pytest.mark.parametrize("body", [{"run_code": "RUN-1"}, {"bag_count": 0}, {"bag_count": 1000}, {"hold_minutes": -5}])
def test_a_malformed_correction_is_refused(farm, body):
    run = farm.sterilization_run()
    assert farm.client.patch(f"/api/sterilization-runs/{run['sterilization_run_id']}", json=body).status_code == 422


def test_a_run_code_already_in_use_is_refused_with_a_sentence(farm):
    farm.sterilization_run(run_code="261109A")
    second = farm.sterilization_run(run_code="261109B")
    refused = farm.client.patch(f"/api/sterilization-runs/{second['sterilization_run_id']}", json={"run_code": "261109A"})
    assert refused.status_code == 409
    assert "already exists" in refused.json()["detail"]
    assert farm.get(f"/api/sterilization-runs/{second['sterilization_run_id']}")["run_code"] == "261109B"


def test_only_an_administrator_corrects_a_run(farm, operator_client):
    sterilization = farm.sterilization_run()
    pasteurization = farm.pasteurization_run()
    for path in (
        f"/api/sterilization-runs/{sterilization['sterilization_run_id']}",
        f"/api/pasteurization-runs/{pasteurization['pasteurization_run_id']}",
    ):
        assert operator_client.patch(path, json={"notes": "x"}).status_code == 403
    assert farm.client.patch("/api/sterilization-runs/999", json={"notes": "x"}).status_code == 404
    assert farm.client.patch("/api/pasteurization-runs/999", json={"notes": "x"}).status_code == 404
