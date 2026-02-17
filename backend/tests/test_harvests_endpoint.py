import pytest
pytest.importorskip("httpx")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import app
from app import models


def _seed_minimum_data(db):
    recipe = models.SubstrateRecipeVersion(name="Test Recipe")
    fill = models.FillProfile(name="Test Fill", target_dry_kg_per_bag=1.0, target_water_kg_per_bag=1.0)
    db.add(recipe)
    db.add(fill)
    db.commit()
    db.refresh(recipe)
    db.refresh(fill)

    batch = models.SubstrateBatch(
        name="TEST-BATCH-HARVEST",
        substrate_recipe_version_id=recipe.substrate_recipe_version_id,
        fill_profile_id=fill.fill_profile_id,
        bag_count=1,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    bag = models.SubstrateBag(bag_id="TEST-BATCH-HARVEST-0001", substrate_batch_id=batch.substrate_batch_id)
    db.add(bag)
    db.commit()
    db.refresh(bag)
    return batch


def test_post_harvests_creates_harvest_event():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    models.Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        with TestingSessionLocal() as db:
            batch = _seed_minimum_data(db)

        payload = {
            "substrate_batch_id": batch.substrate_batch_id,
            "flush_number": 1,
            "harvested_kg": 0.5,
            "notes": "Good",
        }
        res = client.post("/api/harvests", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body["substrate_batch_id"] == batch.substrate_batch_id
        assert body["flush_number"] == 1
        assert body["harvested_kg"] == 0.5
        assert body["notes"] == "Good"
        assert body["bag_id"] == "TEST-BATCH-HARVEST-0001"
        assert "harvest_event_id" in body
        assert "harvested_at" in body
    finally:
        app.dependency_overrides.clear()
