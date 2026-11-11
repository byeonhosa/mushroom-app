"""Recipes, fill profiles, grain types, ingredients and liquid cultures:
add, edit, deactivate, and a culture's parent (SRS REF-3 to REF-7, REF-10,
REF-12, REF-14), through the API."""

import pytest


def _patch(client, path, body, expect=200):
    response = client.patch(path, json=body)
    assert response.status_code == expect, f"PATCH {path} -> {response.status_code}: {response.text}"
    return response.json()


# -------------------------------------------------------------------- recipes

def test_an_administrator_adds_and_edits_a_spawn_recipe(farm):
    recipe = farm.post("/api/spawn-recipes", {"recipe_code": " millet-2 ", "notes": "Millet, 1% gypsum"})
    assert recipe["recipe_code"] == "MILLET-2"
    assert recipe["is_active"] is True

    saved = _patch(farm.client, f"/api/spawn-recipes/{recipe['spawn_recipe_id']}", {"notes": "Millet, 2% gypsum"})
    assert saved["notes"] == "Millet, 2% gypsum"
    assert saved["recipe_code"] == "MILLET-2"

    codes = [row["recipe_code"] for row in farm.get("/api/spawn-recipes")]
    assert codes == ["SR1", "MILLET-2"]


def test_an_administrator_adds_and_edits_a_substrate_recipe(farm):
    recipe = farm.post(
        "/api/substrate-recipe-versions",
        {"name": "Hardwood and bran", "recipe_code": "hb", "notes": "80% oak, 20% wheat bran"},
    )
    assert (recipe["name"], recipe["recipe_code"], recipe["is_active"]) == ("Hardwood and bran", "HB", True)

    saved = _patch(
        farm.client,
        f"/api/substrate-recipe-versions/{recipe['substrate_recipe_version_id']}",
        {"name": "Hardwood and bran 80/20"},
    )
    assert saved["name"] == "Hardwood and bran 80/20"
    assert saved["recipe_code"] == "HB"


@pytest.mark.parametrize(
    "path, body",
    [
        ("/api/spawn-recipes", {"recipe_code": "SR1"}),
        ("/api/substrate-recipe-versions", {"name": "Another", "recipe_code": "MM"}),
        ("/api/substrate-recipe-versions", {"name": "Masters Mix", "recipe_code": "M2"}),
        ("/api/fill-profiles", {"name": "Standard", "target_dry_kg_per_bag": 1, "target_water_kg_per_bag": 1}),
        ("/api/grain-types", {"name": "Rye"}),
    ],
)
def test_a_second_record_with_the_same_code_or_name_is_refused_with_a_sentence(farm, path, body):
    response = farm.client.post(path, json=body)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.parametrize(
    "path, body",
    [
        ("/api/spawn-recipes", {"recipe_code": "  "}),
        ("/api/spawn-recipes", {"recipe_code": "rye mix"}),
        ("/api/substrate-recipe-versions", {"name": " ", "recipe_code": "X1"}),
        ("/api/fill-profiles", {"name": "Empty", "target_dry_kg_per_bag": 0, "target_water_kg_per_bag": 1}),
        ("/api/fill-profiles", {"name": "Negative", "target_dry_kg_per_bag": 1, "target_water_kg_per_bag": -1}),
        ("/api/grain-types", {"name": ""}),
    ],
)
def test_an_empty_name_a_malformed_code_or_an_impossible_weight_is_refused(farm, path, body):
    assert farm.client.post(path, json=body).status_code == 422


# -------------------------------------------------------------- fill profiles

def test_a_fill_profile_can_be_edited_and_bags_already_created_keep_their_weight(farm):
    profile_id = farm.fill_profile["fill_profile_id"]
    run = farm.pasteurization_run(bag_count=2)
    before = farm.post("/api/bags/substrate", {"pasteurization_run_id": run["pasteurization_run_id"], "bag_count": 1})

    saved = _patch(farm.client, f"/api/fill-profiles/{profile_id}", {"target_dry_kg_per_bag": 1.2})
    assert saved["target_dry_kg_per_bag"] == pytest.approx(1.2)
    assert saved["name"] == "Standard"

    after = farm.post("/api/bags/substrate", {"pasteurization_run_id": run["pasteurization_run_id"], "bag_count": 1})
    assert before[0]["target_dry_kg"] == pytest.approx(1.0)
    assert after[0]["target_dry_kg"] == pytest.approx(1.2)
    assert farm.get(f"/api/bags/{before[0]['bag_id']}")["target_dry_kg"] == pytest.approx(1.0)


def test_a_null_for_a_required_field_leaves_it_as_it_was(farm):
    profile_id = farm.fill_profile["fill_profile_id"]
    saved = _patch(farm.client, f"/api/fill-profiles/{profile_id}", {"name": None, "notes": "Unicorn bags"})
    assert saved["name"] == "Standard"
    assert saved["notes"] == "Unicorn bags"
    assert _patch(farm.client, f"/api/fill-profiles/{profile_id}", {"notes": None})["notes"] is None


# ---------------------------------------------------------------- deactivate

def test_a_deactivated_record_stays_listed_and_cannot_be_used_for_new_work(farm):
    """REF-14: nothing in use is deleted; it is switched off and stays visible."""
    run = farm.sterilization_run()
    lot_before = farm.mix_lot

    for path in (
        f"/api/spawn-recipes/{farm.spawn_recipe_id}",
        f"/api/grain-types/{farm.grain_type['grain_type_id']}",
        f"/api/substrate-recipe-versions/{farm.substrate_recipe_id}",
        f"/api/fill-profiles/{farm.fill_profile['fill_profile_id']}",
    ):
        assert _patch(farm.client, path, {"is_active": False})["is_active"] is False

    # Still listed, marked inactive.
    assert [row["is_active"] for row in farm.get("/api/spawn-recipes")] == [False]
    assert [row["is_active"] for row in farm.get("/api/grain-types")] == [False]
    assert [row["is_active"] for row in farm.get("/api/substrate-recipe-versions")] == [False]
    assert [row["is_active"] for row in farm.get("/api/fill-profiles")] == [False]

    # The run and the mix lot that used them are untouched.
    assert farm.get(f"/api/sterilization-runs/{run['sterilization_run_id']}")["spawn_recipe_id"] == farm.spawn_recipe_id
    assert lot_before["mix_lot_id"] in [row["mix_lot_id"] for row in farm.get("/api/mix-lots")]

    # New work cannot use them.
    refused = farm.client.post(
        "/api/sterilization-runs",
        json={
            "run_code": farm.next_code("sterilization"),
            "spawn_recipe_id": farm.spawn_recipe_id,
            "grain_type_id": farm.grain_type["grain_type_id"],
            "unloaded_at": "2026-11-10T15:00:00Z",
            "bag_count": 2,
        },
    )
    assert refused.status_code == 400
    assert "spawn recipe is deactivated" in refused.json()["detail"]

    refused = farm.client.post(
        "/api/mix-lots",
        json={
            "lot_code": "LOT-2",
            "substrate_recipe_version_id": farm.substrate_recipe_id,
            "fill_profile_id": farm.fill_profile["fill_profile_id"],
        },
    )
    assert refused.status_code == 400
    assert "substrate recipe is deactivated" in refused.json()["detail"]

    refused = farm.client.post(
        "/api/pasteurization-runs",
        json={
            "run_code": farm.next_code("pasteurization"),
            "mix_lot_id": farm.mix_lot["mix_lot_id"],
            "substrate_recipe_version_id": farm.substrate_recipe_id,
            "unloaded_at": "2026-11-10T15:00:00Z",
            "bag_count": 2,
        },
    )
    assert refused.status_code == 400

    # Switched back on, it works again.
    _patch(farm.client, f"/api/spawn-recipes/{farm.spawn_recipe_id}", {"is_active": True})
    _patch(farm.client, f"/api/grain-types/{farm.grain_type['grain_type_id']}", {"is_active": True})
    farm.sterilization_run()


def test_an_ingredient_can_be_renamed_and_deactivated(farm):
    ingredient = farm.post("/api/ingredients", {"name": "Soy hulls", "category": "Supplement"})
    assert ingredient["is_active"] is True
    saved = _patch(
        farm.client, f"/api/ingredients/{ingredient['ingredient_id']}", {"name": "Soy hull pellets", "is_active": False}
    )
    assert (saved["name"], saved["category"], saved["is_active"]) == ("Soy hull pellets", "Supplement", False)
    assert farm.client.patch("/api/ingredients/999", json={"name": "x"}).status_code == 404


def test_an_unknown_record_is_not_found(farm):
    for path in (
        "/api/spawn-recipes/999",
        "/api/substrate-recipe-versions/999",
        "/api/fill-profiles/999",
        "/api/liquid-cultures/999",
    ):
        assert farm.client.patch(path, json={"notes": "x"}).status_code == 404, path


# -------------------------------------------------------------------- access

def test_an_operator_reads_recipes_and_profiles_but_cannot_change_them(farm, operator_client):
    for path in ("/api/spawn-recipes", "/api/substrate-recipe-versions", "/api/fill-profiles", "/api/grain-types"):
        assert operator_client.get(path).status_code == 200, path

    attempts = [
        ("post", "/api/spawn-recipes", {"recipe_code": "NEW"}),
        ("patch", f"/api/spawn-recipes/{farm.spawn_recipe_id}", {"is_active": False}),
        ("post", "/api/substrate-recipe-versions", {"name": "New", "recipe_code": "NW"}),
        ("patch", f"/api/substrate-recipe-versions/{farm.substrate_recipe_id}", {"is_active": False}),
        ("patch", f"/api/fill-profiles/{farm.fill_profile['fill_profile_id']}", {"is_active": False}),
        ("patch", f"/api/grain-types/{farm.grain_type['grain_type_id']}", {"is_active": False}),
    ]
    for method, path, body in attempts:
        assert getattr(operator_client, method)(path, json=body).status_code == 403, (method, path)


# ------------------------------------------------------------ liquid cultures

def test_a_culture_names_the_culture_it_was_made_from(farm):
    parent = farm.liquid_culture
    child = farm.post(
        "/api/liquid-cultures",
        {
            "culture_code": "LC-LM-2",
            "species_id": farm.species["species_id"],
            "parent_liquid_culture_id": parent["liquid_culture_id"],
        },
    )
    assert child["parent_liquid_culture_id"] == parent["liquid_culture_id"]
    assert child["parent_culture_code"] == "LC-LM-1"

    listed = {row["culture_code"]: row for row in farm.get("/api/liquid-cultures")}
    assert listed["LC-LM-2"]["parent_culture_code"] == "LC-LM-1"
    assert listed["LC-LM-1"]["parent_culture_code"] is None


def test_a_culture_s_parent_must_exist_be_of_its_species_and_not_be_its_own_descendant(farm):
    species_id = farm.species["species_id"]
    first = farm.liquid_culture
    second = farm.post(
        "/api/liquid-cultures",
        {"culture_code": "LC-LM-2", "species_id": species_id, "parent_liquid_culture_id": first["liquid_culture_id"]},
    )
    third = farm.post(
        "/api/liquid-cultures",
        {"culture_code": "LC-LM-3", "species_id": species_id, "parent_liquid_culture_id": second["liquid_culture_id"]},
    )

    # Its own parent, and a loop two steps long.
    for culture, parent in ((first, first), (first, third)):
        refused = farm.client.patch(
            f"/api/liquid-cultures/{culture['liquid_culture_id']}",
            json={"parent_liquid_culture_id": parent["liquid_culture_id"]},
        )
        assert refused.status_code == 400
        assert "descendants" in refused.json()["detail"]

    oyster = farm.post("/api/species", {"code": "BO", "name": "Blue Oyster"})
    other = farm.post("/api/liquid-cultures", {"culture_code": "LC-BO-1", "species_id": oyster["species_id"]})
    refused = farm.client.patch(
        f"/api/liquid-cultures/{other['liquid_culture_id']}",
        json={"parent_liquid_culture_id": first["liquid_culture_id"]},
    )
    assert refused.status_code == 400
    assert "same species" in refused.json()["detail"]

    missing = farm.client.post(
        "/api/liquid-cultures",
        json={"culture_code": "LC-LM-9", "species_id": species_id, "parent_liquid_culture_id": 999},
    )
    assert missing.status_code == 404

    # The link can be removed again.
    cleared = _patch(farm.client, f"/api/liquid-cultures/{third['liquid_culture_id']}", {"parent_liquid_culture_id": None})
    assert cleared["parent_liquid_culture_id"] is None


def test_a_deactivated_culture_leaves_the_pick_list_and_cannot_inoculate(farm, operator_client):
    culture_id = farm.liquid_culture["liquid_culture_id"]
    run = farm.sterilization_run(bag_count=2)
    farm.post("/api/bags/spawn", {"sterilization_run_id": run["sterilization_run_id"], "bag_count": 2})
    session = {
        "sterilization_run_id": run["sterilization_run_id"],
        "source_type": "LIQUID_CULTURE",
        "liquid_culture_id": culture_id,
        "bag_count": 1,
    }
    made = farm.post("/api/spawn-inoculations/batch", session)[0]

    # An operator records cultures (D-018), so an operator can retire one.
    saved = _patch(operator_client, f"/api/liquid-cultures/{culture_id}", {"is_active": False, "notes": "Cloudy"})
    assert (saved["is_active"], saved["notes"]) == (False, "Cloudy")

    assert farm.get("/api/liquid-cultures") == []
    assert [row["culture_code"] for row in farm.get("/api/liquid-cultures?active_only=false")] == ["LC-LM-1"]
    assert farm.client.post("/api/spawn-inoculations/batch", json=session).status_code in (400, 404)
    # The bag made from it still names it.
    assert farm.get(f"/api/bags/{made['bag_id']}")["source_liquid_culture_code"] == "LC-LM-1"


def test_a_culture_s_code_and_species_cannot_be_changed_after_the_fact(farm):
    culture_id = farm.liquid_culture["liquid_culture_id"]
    saved = _patch(farm.client, f"/api/liquid-cultures/{culture_id}", {"culture_code": "LC-OTHER", "source": "Lab"})
    assert saved["culture_code"] == "LC-LM-1"
    assert saved["source"] == "Lab"


# ------------------------------------------------------- mix lots, ingredients

def test_an_administrator_corrects_a_mix_lot(farm, operator_client):
    lot_id = farm.mix_lot["mix_lot_id"]
    saved = _patch(
        farm.client,
        f"/api/mix-lots/{lot_id}",
        {"lot_code": " MIX-261109A ", "mixed_at": "2026-11-09T12:30:00Z", "notes": "Wetter than usual"},
    )
    assert saved["lot_code"] == "MIX-261109A"
    assert saved["mixed_at"] == "2026-11-09T12:30:00Z"
    assert saved["notes"] == "Wetter than usual"

    assert operator_client.patch(f"/api/mix-lots/{lot_id}", json={"notes": "x"}).status_code == 403
    assert farm.client.patch("/api/mix-lots/999", json={"notes": "x"}).status_code == 404
    assert farm.client.patch(f"/api/mix-lots/{lot_id}", json={"lot_code": "  "}).status_code == 422

    other = farm.post(
        "/api/mix-lots",
        {
            "lot_code": "LOT-2",
            "substrate_recipe_version_id": farm.substrate_recipe_id,
            "fill_profile_id": farm.fill_profile["fill_profile_id"],
        },
    )
    taken = farm.client.patch(f"/api/mix-lots/{other['mix_lot_id']}", json={"lot_code": "MIX-261109A"})
    assert taken.status_code == 409


def test_a_mix_lot_s_recipe_and_fill_profile_are_fixed_once_a_run_uses_it(farm):
    lot_id = farm.mix_lot["mix_lot_id"]
    recipe = farm.post("/api/substrate-recipe-versions", {"name": "Hardwood", "recipe_code": "HW"})
    profile = farm.post(
        "/api/fill-profiles", {"name": "10 lb block", "target_dry_kg_per_bag": 1.9, "target_water_kg_per_bag": 2.6}
    )
    change = {
        "substrate_recipe_version_id": recipe["substrate_recipe_version_id"],
        "fill_profile_id": profile["fill_profile_id"],
    }

    # A deactivated profile cannot be chosen, even before any run.
    _patch(farm.client, f"/api/fill-profiles/{profile['fill_profile_id']}", {"is_active": False})
    assert farm.client.patch(f"/api/mix-lots/{lot_id}", json=change).status_code == 400
    _patch(farm.client, f"/api/fill-profiles/{profile['fill_profile_id']}", {"is_active": True})

    saved = _patch(farm.client, f"/api/mix-lots/{lot_id}", change)
    assert saved["fill_profile_id"] == profile["fill_profile_id"]

    farm.post(
        "/api/pasteurization-runs",
        {
            "run_code": farm.next_code("pasteurization"),
            "mix_lot_id": lot_id,
            "substrate_recipe_version_id": recipe["substrate_recipe_version_id"],
            "unloaded_at": "2026-11-10T15:00:00Z",
            "bag_count": 2,
        },
    )
    refused = farm.client.patch(
        f"/api/mix-lots/{lot_id}", json={"fill_profile_id": farm.fill_profile["fill_profile_id"]}
    )
    assert refused.status_code == 400
    assert "used by 1 pasteurization run" in refused.json()["detail"]
    # Its notes can still be corrected, and sending what it already has is not a change.
    _patch(farm.client, f"/api/mix-lots/{lot_id}", {"notes": "ok", "fill_profile_id": profile["fill_profile_id"]})


def test_an_ingredient_lot_needs_an_active_ingredient(farm):
    ingredient = farm.post("/api/ingredients", {"name": "Soy hulls"})
    farm.post("/api/ingredient-lots", {"ingredient_id": ingredient["ingredient_id"], "vendor": "Feed store"})
    _patch(farm.client, f"/api/ingredients/{ingredient['ingredient_id']}", {"is_active": False})

    refused = farm.client.post("/api/ingredient-lots", json={"ingredient_id": ingredient["ingredient_id"]})
    assert refused.status_code == 400
    assert "ingredient is deactivated" in refused.json()["detail"]
    assert farm.client.post("/api/ingredient-lots", json={"ingredient_id": 999}).status_code == 404
    # The lot already recorded is still listed.
    assert len(farm.get("/api/ingredient-lots")) == 1
