import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite:///./e2e.sqlite3")
os.environ.setdefault("CORS_ORIGINS", "http://127.0.0.1:3000")
os.environ.setdefault("PYTHONPATH", str(BACKEND_DIR))

from app import models  # noqa: E402


def _sqlite_file_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("The e2e server only supports sqlite DATABASE_URL values.")

    db_path = Path(database_url[len(prefix):])
    if not db_path.is_absolute():
        db_path = (BACKEND_DIR / db_path).resolve()
    return db_path


def _reset_database() -> None:
    db_path = _sqlite_file_path(os.environ["DATABASE_URL"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    engine = create_engine(
        os.environ["DATABASE_URL"],
        connect_args={"check_same_thread": False},
    )
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    db = Session()
    try:
        species = models.MushroomSpecies(code="LM", name="Lion's Mane", is_active=True)
        db.add(species)
        db.flush()

        db.add(
            models.LiquidCulture(
                culture_code="LC-LM-001",
                species_id=species.species_id,
                source="Internal lab",
                is_active=True,
            )
        )
        db.add(models.SpawnRecipe(recipe_code="SR1", notes="Standard rye spawn"))
        db.add(models.GrainType(name="Rye", notes=""))
        substrate_recipe = models.SubstrateRecipeVersion(
            name="Masters Mix",
            recipe_code="MM",
            notes="",
        )
        db.add(substrate_recipe)
        db.flush()

        fill_profile = models.FillProfile(
            name="Standard 1kg Dry",
            target_dry_kg_per_bag=1.0,
            target_water_kg_per_bag=1.25,
            notes="",
        )
        db.add(fill_profile)
        db.flush()

        db.add(
            models.MixLot(
                lot_code="LOT-STD-001",
                substrate_recipe_version_id=substrate_recipe.substrate_recipe_version_id,
                fill_profile_id=fill_profile.fill_profile_id,
                notes="Seeded for browser e2e tests",
            )
        )
        db.commit()
    finally:
        db.close()
        engine.dispose()


def main() -> None:
    _reset_database()

    import uvicorn  # noqa: E402

    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()
