"""One species list with profiles, slugs and website fields (SRS REF-1, REF-2, SPR-1, SPR-2)."""

import re

import pytest
from sqlalchemy import inspect

from app import models, seed_species
from app.seed_species import load_farm_profiles, load_species, seed

# The website's own list (maury-river-mushroom-farm-web, packages/shared/src/species.ts
# at a0ff749). If this app and the website ever disagree on a code or a slug,
# the integration needs a mapping table; this test is what keeps that from
# happening by accident.
WEBSITE_SPECIES = {
    "BO": "blue-oyster", "LM": "lion-s-mane", "STK": "shiitake", "CNT": "chestnut",
    "PO": "pink-oyster", "WO": "white-oyster", "KT": "king-trumpet", "BKO": "black-king-oyster",
    "PP": "pioppino", "MTK": "maitake", "BCH": "beech", "NMK": "nameko",
    "GEN": "golden-enoki", "WEN": "white-enoki", "CDY": "cordyceps", "GO": "golden-oyster",
    "RSH": "reishi", "TT": "turkey-tail",
}
WEBSITE_TIERS = {"year-round", "in-rotation-now", "returning", "wholesale-only", "functional-coming-later"}
WEBSITE_STATES = {
    "available", "low-stock", "sold-out", "coming-soon", "seasonal",
    "preorder", "hidden", "wholesale-only", "inquiry-only",
}
RESEARCHED = {"BKO", "PP", "BCH", "NMK", "GEN", "WEN", "CDY"}


# ---------------------------------------------------------------- the seed file

def test_seed_file_is_the_websites_eighteen_species_in_the_websites_vocabulary():
    entries = load_species()
    assert {e["code"]: e["slug"] for e in entries} == WEBSITE_SPECIES
    assert set(models.AVAILABILITY_TIERS) == WEBSITE_TIERS
    assert set(models.SALE_PATHS) == WEBSITE_STATES
    for entry in entries:
        assert re.fullmatch(r"[A-Z0-9]{2,3}", entry["code"]), entry["code"]  # fits a bag code (BAG-5)
        assert entry["availability_tier"] in WEBSITE_TIERS
        assert entry["sale_path"] in WEBSITE_STATES
        assert entry["data_source"] in ("farm", "researched")
        assert entry["source_note"]
    assert {e["code"] for e in entries if e["data_source"] == "researched"} == RESEARCHED
    # What the farm grows every week as of November 2026.
    assert {e["code"] for e in entries if e["in_rotation_now"]} == {"BO", "WO", "STK", "CNT", "KT", "LM"}


def test_every_profile_value_has_a_column():
    columns = set(inspect(models.SpeciesProfile).columns.keys())
    farm = load_farm_profiles()
    for entry in load_species():
        values = seed_species.profile_values(entry, farm)
        assert set(values) <= columns, set(values) - columns


# ---------------------------------------------------------------- seeding

def test_seed_loads_eighteen_species_each_with_a_profile(db_session):
    counts = seed(db_session)
    assert counts == {"species_added": 18, "species_completed": 0, "profiles_added": 18, "profiles_refreshed": 0}

    species = {s.code: s for s in db_session.query(models.MushroomSpecies).all()}
    assert {code: s.slug for code, s in species.items()} == WEBSITE_SPECIES
    assert all(s.is_active and s.profile is not None for s in species.values())
    assert {code for code, s in species.items() if s.profile.data_source == "researched"} == RESEARCHED

    reishi = species["RSH"]
    assert (reishi.name, reishi.latin_name, reishi.availability_tier, reishi.sale_path, reishi.restrictions) == (
        "Reishi", "Ganoderma lucidum", "functional-coming-later", "coming-soon", "legal-review",
    )
    assert (reishi.profile.code, reishi.profile.common_name) == ("reishi", "Reishi")
    assert reishi.profile.fruiting_temp_f_low == 72 and reishi.profile.fruiting_temp_f_high == 80


def test_seed_is_idempotent(db_session):
    seed(db_session)
    again = seed(db_session)
    assert again == {"species_added": 0, "species_completed": 0, "profiles_added": 0, "profiles_refreshed": 0}
    assert db_session.query(models.MushroomSpecies).count() == 18
    assert db_session.query(models.SpeciesProfile).count() == 18


def test_the_four_oysters_share_the_farms_one_oyster_profile(db_session):
    seed(db_session)
    oysters = [
        db_session.query(models.MushroomSpecies).filter_by(code=code).one().profile for code in ("BO", "WO", "PO", "GO")
    ]
    farm_oyster = load_farm_profiles()["oyster"]
    for profile in oysters:
        assert profile.data_source == "farm"
        assert "shared by the four oyster varieties" in profile.source_note
        assert profile.colonization_days_low == farm_oyster["colonization_days_low"] == 7
        assert profile.biological_efficiency_pct_high == farm_oyster["biological_efficiency_pct_high"] == 200
    assert [p.common_name for p in oysters] == ["Blue Oyster", "White Oyster", "Pink Oyster", "Golden Oyster"]


def test_a_value_no_source_gave_stays_empty_and_is_not_zero(db_session):
    seed(db_session)

    def profile(code):
        return db_session.query(models.MushroomSpecies).filter_by(code=code).one().profile

    # From the farm's sources: no clean figure for lion's mane yield, or oyster's lower CO2 bound.
    assert profile("LM").biological_efficiency_pct_low is None
    assert profile("BO").fruiting_co2_ppm_low is None and profile("BO").fruiting_co2_ppm_high == 1000
    # Researched: nobody gave beech's spawn run, or nameko's biological efficiency.
    assert profile("BCH").colonization_days_low is None and profile("BCH").pin_to_harvest_days_low is None
    assert profile("NMK").biological_efficiency_pct_high is None
    assert profile("BCH").biological_efficiency_pct_low == 66


def test_seed_completes_an_existing_species_without_changing_what_is_there(db_session):
    """Production already holds Lion's Mane with no slug: it is completed, not duplicated."""
    existing = models.MushroomSpecies(code="LM", name="Lions Mane (ours)", is_active=False, notes="keep me")
    db_session.add(existing)
    db_session.commit()

    counts = seed(db_session)
    assert (counts["species_added"], counts["species_completed"], counts["profiles_added"]) == (17, 1, 18)
    db_session.refresh(existing)
    assert db_session.query(models.MushroomSpecies).filter_by(code="LM").count() == 1
    # Filled in:
    assert (existing.slug, existing.latin_name, existing.availability_tier, existing.sale_path) == (
        "lion-s-mane", "Hericium erinaceus", "year-round", "available",
    )
    # Left alone:
    assert (existing.name, existing.is_active, existing.notes) == ("Lions Mane (ours)", False, "keep me")
    assert existing.profile.common_name == "Lions Mane (ours)"


def test_seed_never_overwrites_what_an_administrator_changed(db_session):
    seed(db_session)
    blue = db_session.query(models.MushroomSpecies).filter_by(code="BO").one()
    blue.sale_path = "sold-out"
    blue.in_rotation_now = False
    blue.profile.colonization_days_low = 10
    db_session.commit()

    seed(db_session)
    db_session.refresh(blue)
    assert (blue.sale_path, blue.in_rotation_now, blue.profile.colonization_days_low) == ("sold-out", False, 10)

    # Asked for on purpose, the profiles go back to the repository's values. Nothing else does.
    counts = seed(db_session, refresh_profiles=True)
    assert counts["profiles_refreshed"] == 18
    db_session.refresh(blue)
    assert blue.profile.colonization_days_low == 7
    assert blue.sale_path == "sold-out"


# ---------------------------------------------------------------- API: species

@pytest.fixture
def seeded(client, db_session):
    seed(db_session)
    return client


def test_species_list_carries_slug_and_website_fields(seeded):
    rows = {row["code"]: row for row in seeded.get("/api/species").json()}
    assert len(rows) == 18
    assert rows["GO"] == {
        "species_id": rows["GO"]["species_id"],
        "code": "GO",
        "name": "Golden Oyster",
        "latin_name": "Pleurotus citrinopileatus",
        "notes": None,
        "is_active": True,
        "slug": "golden-oyster",
        "availability_tier": "wholesale-only",
        "sale_path": "wholesale-only",
        "in_rotation_now": False,
        "restrictions": None,
    }


def test_a_new_species_gets_a_slug_from_its_name_and_starts_hidden(client):
    created = client.post("/api/species", json={"code": "wc", "name": "Wine Cap's Best"})
    assert created.status_code == 200, created.text
    body = created.json()
    assert (body["code"], body["slug"], body["sale_path"], body["in_rotation_now"], body["availability_tier"]) == (
        "WC", "wine-cap-s-best", "hidden", False, None,
    )
    # A second species cannot take the same slug.
    clash = client.post("/api/species", json={"code": "W2", "name": "Wine Cap's Best"})
    assert clash.status_code == 409 and "wine-cap-s-best" in clash.json()["detail"]

    explicit = client.post("/api/species", json={"code": "EL", "name": "Elm Oyster", "slug": "elm-oyster", "sale_path": "seasonal"})
    assert explicit.status_code == 200 and explicit.json()["slug"] == "elm-oyster"


@pytest.mark.parametrize(
    "body",
    [
        {"availability_tier": "sometimes"},
        {"sale_path": "for-sale"},
        {"slug": "Not A Slug"},
        {"slug": "trailing-"},
    ],
)
def test_values_outside_the_websites_vocabulary_are_refused(client, body):
    response = client.post("/api/species", json={"code": "ZZ", "name": "Zed", **body})
    assert response.status_code == 422, response.text


def test_a_slug_never_changes_once_set_and_website_fields_can_be_edited(seeded):
    lions_mane = next(row for row in seeded.get("/api/species").json() if row["code"] == "LM")
    path = f"/api/species/{lions_mane['species_id']}"

    refused = seeded.patch(path, json={"slug": "lions-mane"})
    assert refused.status_code == 400
    assert "cannot be changed once set" in refused.json()["detail"]
    # Sending the same slug back, as an edit form does, is not a change.
    assert seeded.patch(path, json={"slug": "lion-s-mane", "name": "Lion's Mane"}).status_code == 200

    edited = seeded.patch(
        path, json={"availability_tier": "returning", "sale_path": "sold-out", "in_rotation_now": False, "restrictions": None}
    )
    assert edited.status_code == 200
    assert (edited.json()["slug"], edited.json()["availability_tier"], edited.json()["sale_path"], edited.json()["in_rotation_now"], edited.json()["restrictions"]) == (
        "lion-s-mane", "returning", "sold-out", False, None,
    )
    assert seeded.patch(path, json={"sale_path": "nonsense"}).status_code == 422


def test_a_species_without_a_slug_can_be_given_one_once(client, db_session):
    legacy = models.MushroomSpecies(code="OLD", name="Legacy", is_active=True)
    db_session.add(legacy)
    db_session.commit()
    path = f"/api/species/{legacy.species_id}"
    assert client.patch(path, json={"slug": "legacy-variety"}).json()["slug"] == "legacy-variety"
    assert client.patch(path, json={"slug": "something-else"}).status_code == 400


def test_renaming_a_species_renames_its_profile(seeded):
    king = next(row for row in seeded.get("/api/species").json() if row["code"] == "KT")
    seeded.patch(f"/api/species/{king['species_id']}", json={"name": "King Oyster"})
    assert seeded.get("/api/species-profiles/king-trumpet").json()["common_name"] == "King Oyster"


# ---------------------------------------------------------------- API: profiles (SPR-1, SPR-2)

def test_profile_list_covers_all_eighteen_and_says_which_are_researched(seeded):
    rows = seeded.get("/api/species-profiles").json()
    assert len(rows) == 18
    assert [row["common_name"] for row in rows] == sorted(row["common_name"] for row in rows)
    by_code = {row["species_code"]: row for row in rows}
    assert {code for code, row in by_code.items() if row["data_source"] == "researched"} == RESEARCHED
    assert by_code["PP"]["source_note"].startswith("Researched from suppliers and papers")
    assert by_code["PP"]["code"] == "pioppino"
    assert by_code["LM"]["biological_efficiency_pct_low"] is None  # null stays null in JSON


def test_a_profile_is_found_by_slug_or_by_label_code(seeded):
    by_slug = seeded.get("/api/species-profiles/reishi")
    by_code = seeded.get("/api/species-profiles/RSH")
    assert by_slug.status_code == by_code.status_code == 200
    assert by_slug.json() == by_code.json()
    assert by_slug.json()["fruiting_temp_f_low"] == 72 and by_slug.json()["species_code"] == "RSH"
    assert seeded.get("/api/species-profiles/does-not-exist").status_code == 404


def test_an_operator_reads_species_and_profiles_but_cannot_change_them(seeded, operator_client):
    assert len(operator_client.get("/api/species").json()) == 18
    assert operator_client.get("/api/species-profiles/LM").status_code == 200
    assert operator_client.post("/api/species", json={"code": "ZZ", "name": "Zed"}).status_code == 403
