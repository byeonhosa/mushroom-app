"""Idempotent seeder for the species_profiles reference table.

Reads backend/app/seeds/mushroom_species.json and upserts each species by its
JSON ``id`` (stored as ``code``), so re-running never creates duplicate rows.
JSON nulls are written through as SQL NULL — values are not coerced to 0 or "".

Run inside the API container (or any env with DATABASE_URL set):

    python -m app.seed_species

The table itself is created by migration 022_species_profiles.sql; run
``python -m app.migrate`` first.
"""

import json
from pathlib import Path

from .db import SessionLocal
from . import models

SEED_FILE = Path(__file__).parent / "seeds" / "mushroom_species.json"

# Every JSON key except the natural key ``id`` maps 1:1 onto a model column.
_KEY_TO_COLUMN = {"id": "code"}


def load_seed_records(path: Path = SEED_FILE) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["species"]


def upsert_species(db, record: dict) -> models.SpeciesProfile:
    code = record["id"]
    obj = (
        db.query(models.SpeciesProfile)
        .filter(models.SpeciesProfile.code == code)
        .one_or_none()
    )
    if obj is None:
        obj = models.SpeciesProfile(code=code)
        db.add(obj)

    for key, value in record.items():
        column = _KEY_TO_COLUMN.get(key, key)
        # Preserve JSON null as SQL NULL; no coercion to 0 / "".
        setattr(obj, column, value)
    return obj


def seed(db=None, path: Path = SEED_FILE) -> int:
    """Upsert all species from the seed file. Returns the row count processed."""
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        records = load_seed_records(path)
        for record in records:
            upsert_species(db, record)
        db.commit()
        return len(records)
    finally:
        if own_session:
            db.close()


def main():
    count = seed()
    print(f"Seeded {count} species profiles from {SEED_FILE}")


if __name__ == "__main__":
    main()
