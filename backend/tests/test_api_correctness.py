"""WP-1 input, error and consistency fixes, exercised through the HTTP API.

RUN-3 planned bag count, RUN-7 duplicate codes, RUN-8 sort fields, RUN-4 /
RPT-3 ready count, SRS 5.2 UTC offsets, MNT-3 one status path, MNT-6 zones.
"""

import re
from datetime import datetime, timedelta, timezone

import pytest

from app import crud, models
from app.crud_status import _bag_history_snapshot

from .conftest import iso


# ---------------------------------------------------------------- RUN-3

@pytest.mark.parametrize("bag_count", [0, -5, 1000])
def test_run_planned_bag_count_must_be_a_positive_whole_number_within_range(farm, bag_count):
    for path, body in (
        (
            "/api/sterilization-runs",
            {
                "run_code": "261109A",
                "spawn_recipe_id": farm.spawn_recipe_id,
                "grain_type_id": farm.grain_type["grain_type_id"],
            },
        ),
        (
            "/api/pasteurization-runs",
            {
                "run_code": "261109A",
                "mix_lot_id": farm.mix_lot["mix_lot_id"],
                "substrate_recipe_version_id": farm.substrate_recipe_id,
            },
        ),
    ):
        response = farm.client.post(
            path, json={**body, "unloaded_at": iso(farm.now), "bag_count": bag_count}
        )
        assert response.status_code == 422, response.text

    assert farm.get("/api/sterilization-runs") == []
    assert farm.get("/api/pasteurization-runs") == []


def test_run_planned_bag_count_refuses_a_fraction(farm):
    response = farm.client.post(
        "/api/pasteurization-runs",
        json={
            "run_code": "261109A",
            "mix_lot_id": farm.mix_lot["mix_lot_id"],
            "substrate_recipe_version_id": farm.substrate_recipe_id,
            "unloaded_at": iso(farm.now),
            "bag_count": 2.5,
        },
    )
    assert response.status_code == 422


# ---------------------------------------------------------------- RUN-7

def test_duplicate_run_code_is_refused_with_a_message_not_a_server_error(farm):
    farm.sterilization_run(run_code="261109A")
    farm.pasteurization_run(run_code="261109A")

    again = farm.client.post(
        "/api/sterilization-runs",
        json={
            "run_code": "261109A",
            "spawn_recipe_id": farm.spawn_recipe_id,
            "grain_type_id": farm.grain_type["grain_type_id"],
            "unloaded_at": iso(farm.now),
            "bag_count": 2,
        },
    )
    assert again.status_code == 409
    assert again.json()["detail"] == "Run code already exists."

    again = farm.client.post(
        "/api/pasteurization-runs",
        json={
            "run_code": "261109A",
            "mix_lot_id": farm.mix_lot["mix_lot_id"],
            "substrate_recipe_version_id": farm.substrate_recipe_id,
            "unloaded_at": iso(farm.now),
            "bag_count": 2,
        },
    )
    assert again.status_code == 409
    assert again.json()["detail"] == "Run code already exists."

    # The failed request must not leave the session unusable.
    assert len(farm.get("/api/sterilization-runs")) == 1
    assert len(farm.get("/api/pasteurization-runs")) == 1


@pytest.mark.parametrize(
    "path, body, message",
    [
        ("/api/species", {"code": "LM", "name": "Again"}, "Species code already exists."),
        ("/api/grain-types", {"name": "Rye"}, "Grain type already exists."),
        ("/api/liquid-cultures", {"culture_code": "LC-LM-1", "species_id": 1}, "Liquid culture code already exists."),
    ],
)
def test_duplicate_reference_codes_are_refused_with_a_message(farm, path, body, message):
    response = farm.client.post(path, json=body)
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == message


def test_unanticipated_duplicate_is_still_a_sentence(farm):
    # Fill profile names are unique and the route has no handler of its own:
    # the application-wide handler answers.
    response = farm.client.post(
        "/api/fill-profiles",
        json={"name": "Standard", "target_dry_kg_per_bag": 1.0, "target_water_kg_per_bag": 1.0},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_run_naming_a_missing_reference_record_is_not_found(farm):
    response = farm.client.post(
        "/api/pasteurization-runs",
        json={
            "run_code": "261109A",
            "mix_lot_id": 9999,
            "substrate_recipe_version_id": farm.substrate_recipe_id,
            "unloaded_at": iso(farm.now),
            "bag_count": 2,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Mix lot not found"

    response = farm.client.post(
        "/api/sterilization-runs",
        json={
            "run_code": "261109A",
            "spawn_recipe_id": farm.spawn_recipe_id,
            "grain_type_id": 9999,
            "unloaded_at": iso(farm.now),
            "bag_count": 2,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Grain type not found"


# ---------------------------------------------------------------- RUN-8

def test_sterilization_runs_sort_by_known_fields(farm):
    farm.sterilization_run(run_code="261109B", bag_count=2)
    farm.sterilization_run(run_code="261109A", bag_count=9)

    by_code = farm.get("/api/sterilization-runs?sort_by=run_code&sort_order=asc")
    assert [row["run_code"] for row in by_code] == ["261109A", "261109B"]

    by_count = farm.get("/api/sterilization-runs?sort_by=bag_count&sort_order=desc")
    assert [row["run_code"] for row in by_count] == ["261109A", "261109B"]


@pytest.mark.parametrize("sort_by", ["spawn_recipe", "grain_type", "metadata", "no_such_field", "__class__"])
def test_unknown_sort_field_is_refused_with_a_message(farm, sort_by):
    farm.sterilization_run()
    response = farm.client.get(f"/api/sterilization-runs?sort_by={sort_by}")
    assert response.status_code == 400
    assert "Cannot sort by" in response.json()["detail"]
    assert "run_code" in response.json()["detail"]


def test_unknown_sort_order_is_refused(farm):
    response = farm.client.get("/api/sterilization-runs?sort_order=sideways")
    assert response.status_code == 400


# ---------------------------------------------------------------- SRS 5.2

_OFFSET = re.compile(r"(Z|[+-]\d{2}:\d{2})$")


def _times_without_offset(payload, path="$"):
    """Every `*_at` string in a JSON payload that lacks a UTC offset."""
    found = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            here = f"{path}.{key}"
            if isinstance(value, str) and key.endswith("_at"):
                if not _OFFSET.search(value):
                    found.append(f"{here}={value}")
            else:
                found.extend(_times_without_offset(value, here))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            found.extend(_times_without_offset(value, f"{path}[{index}]"))
    return found


def test_every_time_the_api_sends_carries_its_utc_offset(farm):
    run, bags = farm.inoculated_substrate_bags(bag_count=2)
    first = bags[0]["bag_id"]
    farm.post(f"/api/bags/{first}/incubation-start")
    farm.post(f"/api/bags/{first}/ready")
    farm.post(f"/api/bags/{first}/fruiting-start")
    harvest = farm.post("/api/harvest-events", {"bag_id": first, "flush_number": 1, "fresh_weight_kg": 0.4})
    farm.post(f"/api/bags/{bags[1]['bag_id']}/disposal", {"disposal_reason": "CONTAMINATION"})

    sterilization_run_id = farm.get("/api/sterilization-runs")[0]["sterilization_run_id"]
    responses = {
        "harvest": harvest,
        "health": farm.get("/api/health"),
        "bags": farm.get("/api/bags"),
        "bag": farm.get(f"/api/bags/{first}"),
        "events": farm.get(f"/api/bags/{first}/status-events"),
        "harvests": farm.get(f"/api/bags/{first}/harvest-events"),
        "inoculation": farm.get(f"/api/bags/{first}/inoculation"),
        "past_runs": farm.get("/api/pasteurization-runs"),
        "past_detail": farm.get(f"/api/pasteurization-runs/{run['pasteurization_run_id']}/detail"),
        "ster_runs": farm.get("/api/sterilization-runs"),
        "ster_detail": farm.get(f"/api/sterilization-runs/{sterilization_run_id}/detail"),
        "mix_lots": farm.get("/api/mix-lots"),
        "cultures": farm.get("/api/liquid-cultures"),
        "dashboard": farm.get("/api/dashboard/overview"),
        "report": farm.get("/api/reports/production"),
    }
    missing = {name: _times_without_offset(body) for name, body in responses.items()}
    assert {name: found for name, found in missing.items() if found} == {}

    # The same harvest reads the same instant wherever it is shown.
    detail = responses["bag"]
    harvest_event = next(e for e in detail["status_events"] if e["event_type"] == "HARVEST_RECORDED")
    as_instant = lambda text: datetime.fromisoformat(text.replace("Z", "+00:00"))  # noqa: E731
    assert as_instant(detail["harvest_events"][0]["harvested_at"]) == as_instant(harvest["harvested_at"])
    assert as_instant(harvest_event["occurred_at"]) == as_instant(harvest["harvested_at"])


def test_a_time_without_an_offset_is_refused(farm):
    response = farm.client.post(
        "/api/pasteurization-runs",
        json={
            "run_code": "261109A",
            "mix_lot_id": farm.mix_lot["mix_lot_id"],
            "substrate_recipe_version_id": farm.substrate_recipe_id,
            "unloaded_at": "2026-11-09T14:00:00",
            "bag_count": 2,
        },
    )
    assert response.status_code == 422
    assert farm.get("/api/pasteurization-runs") == []


def test_a_time_with_an_offset_is_stored_as_the_same_instant(farm):
    run = farm.pasteurization_run(run_code="261109A", unloaded_at="2026-11-09T09:30:00-05:00")
    assert datetime.fromisoformat(run["unloaded_at"].replace("Z", "+00:00")) == datetime(
        2026, 11, 9, 14, 30, tzinfo=timezone.utc
    )


# ---------------------------------------------------------------- RUN-4 / RPT-3

def test_pasteurization_summary_counts_only_bags_that_reached_ready(farm):
    run, bags = farm.inoculated_substrate_bags(bag_count=4)
    reached_ready, contaminated_early, disposed_after_ready, untouched = (b["bag_id"] for b in bags)

    for bag_id in (reached_ready, disposed_after_ready):
        farm.post(f"/api/bags/{bag_id}/incubation-start")
        farm.post(f"/api/bags/{bag_id}/ready")
    farm.post(f"/api/bags/{contaminated_early}/disposal", {"disposal_reason": "CONTAMINATION"})
    farm.post(f"/api/bags/{disposed_after_ready}/disposal", {"disposal_reason": "CONTAMINATION"})

    summary = farm.get(f"/api/pasteurization-runs/{run['pasteurization_run_id']}/detail")["summary"]
    assert summary["total_bags"] == 4
    assert summary["inoculated_bags"] == 4
    # Two bags were marked ready. The one contaminated before it colonized never was.
    assert summary["ready_bags"] == 2
    assert summary["contaminated_bags"] == 2
    assert summary["fruiting_bags"] == 0
    assert untouched


# ---------------------------------------------------------------- MNT-3

def test_status_is_the_same_with_and_without_event_history(db_session, farm):
    """A bag carrying only cached columns reads exactly as one with events."""
    _, bags = farm.inoculated_substrate_bags(bag_count=1)
    bag_id = bags[0]["bag_id"]
    stages = [
        ("INOCULATED", None),
        ("INCUBATING", f"/api/bags/{bag_id}/incubation-start"),
        ("READY", f"/api/bags/{bag_id}/ready"),
        ("FRUITING", f"/api/bags/{bag_id}/fruiting-start"),
    ]
    for expected, path in stages:
        if path:
            farm.post(path)
        bag = crud.get_bag(db_session, bag_id)
        with_history = _bag_history_snapshot(bag)
        assert with_history["status"] == expected

        events = list(bag.status_events)
        bag.status_events = []
        try:
            without_history = _bag_history_snapshot(bag)
        finally:
            bag.status_events = events
            db_session.rollback()
        assert without_history["status"] == expected
        assert farm.get(f"/api/bags/{bag_id}")["status"] == expected


def test_a_new_bag_record_starts_at_its_heat_treatment_status(db_session, farm):
    run = farm.sterilization_run(bag_count=1)
    bag = farm.post("/api/bags/spawn", {"sterilization_run_id": run["sterilization_run_id"], "bag_count": 1})[0]
    assert bag["status"] == "STERILIZED"

    # Even if the heat-treatment event were missing, the status does not fall
    # back to a value no screen or filter knows.
    row = crud.get_bag(db_session, bag["bag_id"])
    row.status_events = [e for e in row.status_events if e.event_type != "STERILIZED"]
    assert _bag_history_snapshot(row)["status"] == "STERILIZED"
    db_session.rollback()


def test_list_filter_and_dashboard_queue_agree_on_status(farm):
    _, bags = farm.inoculated_substrate_bags(bag_count=3)
    farm.post(f"/api/bags/{bags[0]['bag_id']}/incubation-start")

    listed = farm.get("/api/bags?bag_type=SUBSTRATE&status=INCUBATING")
    queues = {q["key"]: q["count"] for q in farm.get("/api/dashboard/overview")["queues"]}
    assert len(listed) == queues["substrate_incubating"] == 1


# ---------------------------------------------------------------- MNT-6

def test_zones_table_is_gone_from_the_model():
    assert "zones" not in models.Base.metadata.tables
    assert not hasattr(models, "Zone")
