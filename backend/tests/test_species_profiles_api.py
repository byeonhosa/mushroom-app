"""HTTP tests for the read-only species_profiles reference endpoints."""

import pytest

from app.seed_species import seed


@pytest.fixture(autouse=True)
def _seeded_profiles(db_session):
    seed(db_session)


def test_list_returns_all_species(client):
    resp = client.get("/api/species-profiles")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 8

    reishi = next(s for s in body if s["code"] == "reishi")
    assert reishi["fruiting_temp_f_low"] == 72
    assert reishi["common_name"] == "Reishi"
    # JSON nulls survive the round trip as null, not 0.
    lions_mane = next(s for s in body if s["code"] == "lions_mane")
    assert lions_mane["biological_efficiency_pct_low"] is None


def test_get_by_id_returns_record(client):
    resp = client.get("/api/species-profiles/oyster")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "oyster"
    assert body["common_name"] == "Oyster (common)"
    assert body["substrate_moisture_pct_low"] is None


def test_get_by_id_404_on_unknown_code(client):
    resp = client.get("/api/species-profiles/not-a-species")
    assert resp.status_code == 404
