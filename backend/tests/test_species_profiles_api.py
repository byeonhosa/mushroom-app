"""HTTP tests for the read-only species_profiles reference endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.db import get_db
from app.main import app
from app.seed_species import seed


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    db = Session()
    seed(db)

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()


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
