"""Load the farm's species list and cultivation profiles (SRS REF-1, REF-2, SPR-2).

Reads backend/app/seeds/species.json (the eighteen varieties: code, slug,
name, website fields, and where each profile comes from) and
backend/app/seeds/mushroom_species.json (the eight profiles from the farm's
own sources). Runs at every API container start, after the migrations:

    python -m app.seed_species

It only ever ADDS. A species already in the database keeps its name, its
active flag and anything an administrator has changed; it is given a slug and
the website fields only if it has none yet, and a profile only if it has
none. A slug that is set is never changed. To replace every profile with the
values in the repository, deliberately:

    python -m app.seed_species --refresh-profiles
"""

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from . import models
from .db import SessionLocal

SEED_DIR = Path(__file__).parent / "seeds"
SPECIES_FILE = SEED_DIR / "species.json"
FARM_PROFILES_FILE = SEED_DIR / "mushroom_species.json"

# Keys of a farm profile that are not cultivation values.
_NOT_PROFILE_COLUMNS = {"id", "common_name", "scientific_name"}


def load_species(path: Path = SPECIES_FILE) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["species"]


def load_farm_profiles(path: Path = FARM_PROFILES_FILE) -> dict[str, dict]:
    records = json.loads(Path(path).read_text(encoding="utf-8"))["species"]
    return {record["id"]: record for record in records}


def profile_values(entry: dict, farm_profiles: dict[str, dict]) -> dict:
    """The cultivation values for one species entry, JSON nulls kept as None."""
    if "profile" in entry:
        values = dict(entry["profile"])
    else:
        source = farm_profiles[entry["profile_from"]]
        values = {key: value for key, value in source.items() if key not in _NOT_PROFILE_COLUMNS}
    values["data_source"] = entry["data_source"]
    values["source_note"] = entry.get("source_note")
    return values


def _apply_profile(profile: models.SpeciesProfile, species: models.MushroomSpecies, values: dict) -> None:
    profile.code = species.slug
    profile.common_name = species.name
    profile.scientific_name = species.latin_name
    for column, value in values.items():
        setattr(profile, column, value)


def seed(db=None, *, refresh_profiles: bool = False) -> dict[str, int]:
    """Add what is missing. Returns counts of what was added or filled in."""
    own_session = db is None
    if own_session:
        db = SessionLocal()
    counts = {"species_added": 0, "species_completed": 0, "profiles_added": 0, "profiles_refreshed": 0}
    try:
        farm_profiles = load_farm_profiles()
        for entry in load_species():
            species = db.execute(
                select(models.MushroomSpecies).where(models.MushroomSpecies.code == entry["code"])
            ).scalar_one_or_none()
            if species is None:
                species = models.MushroomSpecies(
                    code=entry["code"],
                    name=entry["name"],
                    latin_name=entry["latin_name"],
                    is_active=True,
                    slug=entry["slug"],
                    availability_tier=entry["availability_tier"],
                    sale_path=entry["sale_path"],
                    in_rotation_now=entry["in_rotation_now"],
                    restrictions=entry["restrictions"],
                )
                db.add(species)
                db.flush()
                counts["species_added"] += 1
            else:
                completed = False
                if species.slug is None:
                    species.slug = entry["slug"]
                    completed = True
                if species.latin_name is None:
                    species.latin_name = entry["latin_name"]
                    completed = True
                # The website fields are set together, once, while they are
                # still as the migration left them.
                if species.availability_tier is None:
                    species.availability_tier = entry["availability_tier"]
                    species.sale_path = entry["sale_path"]
                    species.in_rotation_now = entry["in_rotation_now"]
                    species.restrictions = entry["restrictions"]
                    completed = True
                if completed:
                    db.flush()
                    counts["species_completed"] += 1

            values = profile_values(entry, farm_profiles)
            if species.profile is None:
                profile = models.SpeciesProfile(species_id=species.species_id)
                _apply_profile(profile, species, values)
                db.add(profile)
                counts["profiles_added"] += 1
            elif refresh_profiles:
                _apply_profile(species.profile, species, values)
                counts["profiles_refreshed"] += 1
        db.commit()
        return counts
    finally:
        if own_session:
            db.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.seed_species")
    parser.add_argument(
        "--refresh-profiles",
        action="store_true",
        help="overwrite every cultivation profile with the values in the repository",
    )
    args = parser.parse_args(argv)
    counts = seed(refresh_profiles=args.refresh_profiles)
    print("species seed: " + ", ".join(f"{key}={value}" for key, value in counts.items()))


if __name__ == "__main__":
    main()
