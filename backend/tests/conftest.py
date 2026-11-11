"""Shared fixtures for tests that drive the app through its HTTP API.

`client` is a TestClient on a fresh in-memory SQLite database. `farm` seeds
the reference rows a run needs and offers short helpers for the steps most
tests repeat (create a run, create its bags, inoculate, move bags on).
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.db import get_db
from app.main import app


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        # Same contract as app.db.get_db, on the test's own session.
        try:
            yield db_session
        except Exception:
            db_session.rollback()
            raise

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


class Farm:
    """Reference data plus helpers, all through the API where a route exists."""

    def __init__(self, client: TestClient, db):
        self.client = client
        self.db = db
        self.now = datetime.now(timezone.utc)

        # Recipes have no create route yet (REF-3, REF-4 land in WP-3).
        spawn_recipe = models.SpawnRecipe(recipe_code="SR1", notes="Rye")
        substrate_recipe = models.SubstrateRecipeVersion(name="Masters Mix", recipe_code="MM", notes="")
        db.add_all([spawn_recipe, substrate_recipe])
        db.commit()
        self.spawn_recipe_id = spawn_recipe.spawn_recipe_id
        self.substrate_recipe_id = substrate_recipe.substrate_recipe_version_id

        self.species = self.post("/api/species", {"code": "LM", "name": "Lion's Mane"})
        self.grain_type = self.post("/api/grain-types", {"name": "Rye"})
        self.fill_profile = self.post(
            "/api/fill-profiles",
            {"name": "Standard", "target_dry_kg_per_bag": 1.0, "target_water_kg_per_bag": 1.25},
        )
        self.mix_lot = self.post(
            "/api/mix-lots",
            {
                "lot_code": "LOT-1",
                "substrate_recipe_version_id": self.substrate_recipe_id,
                "fill_profile_id": self.fill_profile["fill_profile_id"],
            },
        )
        self.liquid_culture = self.post(
            "/api/liquid-cultures",
            {"culture_code": "LC-LM-1", "species_id": self.species["species_id"]},
        )

    def post(self, path: str, body: dict | None = None, *, expect: int = 200):
        response = self.client.post(path, json=body or {})
        assert response.status_code == expect, f"POST {path} -> {response.status_code}: {response.text}"
        return response.json()

    def get(self, path: str, *, expect: int = 200):
        response = self.client.get(path)
        assert response.status_code == expect, f"GET {path} -> {response.status_code}: {response.text}"
        return response.json()

    def next_code(self, kind: str, on: str | None = None) -> str:
        """The run code the app proposes for a `sterilization` or `pasteurization` run."""
        query = f"?on={on}" if on else ""
        return self.get(f"/api/{kind}-runs/next-code{query}")["run_code"]

    def sterilization_run(self, run_code: str | None = None, bag_count: int = 4, **extra) -> dict:
        return self.post(
            "/api/sterilization-runs",
            {
                "run_code": run_code or self.next_code("sterilization"),
                "spawn_recipe_id": self.spawn_recipe_id,
                "grain_type_id": self.grain_type["grain_type_id"],
                "unloaded_at": iso(self.now - timedelta(hours=2)),
                "bag_count": bag_count,
                **extra,
            },
        )

    def pasteurization_run(self, run_code: str | None = None, bag_count: int = 4, **extra) -> dict:
        return self.post(
            "/api/pasteurization-runs",
            {
                "run_code": run_code or self.next_code("pasteurization"),
                "mix_lot_id": self.mix_lot["mix_lot_id"],
                "substrate_recipe_version_id": self.substrate_recipe_id,
                "unloaded_at": iso(self.now - timedelta(hours=2)),
                "bag_count": bag_count,
                **extra,
            },
        )

    def ready_spawn_bag(self) -> dict:
        """One spawn bag inoculated from the liquid culture and marked ready."""
        run = self.sterilization_run(bag_count=1)
        self.post("/api/bags/spawn", {"sterilization_run_id": run["sterilization_run_id"], "bag_count": 1})
        bag = self.post(
            "/api/spawn-inoculations/batch",
            {
                "sterilization_run_id": run["sterilization_run_id"],
                "source_type": "LIQUID_CULTURE",
                "liquid_culture_id": self.liquid_culture["liquid_culture_id"],
                "bag_count": 1,
            },
        )[0]
        self.post(f"/api/bags/{bag['bag_id']}/incubation-start")
        return self.post(f"/api/bags/{bag['bag_id']}/ready")

    def inoculated_substrate_bags(self, bag_count: int = 3) -> tuple[dict, list[dict]]:
        """A pasteurization run with `bag_count` bags inoculated from one ready spawn bag."""
        spawn = self.ready_spawn_bag()
        run = self.pasteurization_run(bag_count=bag_count)
        self.post(
            "/api/bags/substrate",
            {"pasteurization_run_id": run["pasteurization_run_id"], "bag_count": bag_count},
        )
        bags = self.post(
            "/api/inoculations/batch",
            {
                "spawn_bag_id": spawn["bag_id"],
                "pasteurization_run_id": run["pasteurization_run_id"],
                "bag_count": bag_count,
            },
        )
        return run, bags


@pytest.fixture
def farm(client, db_session) -> Farm:
    return Farm(client, db_session)
