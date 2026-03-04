"""Bag ID generation: STER-{run_code}-{recipe_code}-{species_code}-{seq} or PAST-..."""
import re
from sqlalchemy.orm import Session
from sqlalchemy import select
from . import models


def _next_seq_for_prefix(db: Session, prefix: str) -> int:
    """Find highest seq for bags matching prefix-{seq} and return next."""
    pattern = f"{re.escape(prefix)}-%"
    rows = db.execute(
        select(models.Bag.bag_id).where(models.Bag.bag_id.like(pattern))
    ).scalars().all()
    max_seq = 0
    for bid in rows:
        if not bid:
            continue
        m = re.match(rf"^{re.escape(prefix)}-(\d+)$", bid)
        if m:
            max_seq = max(max_seq, int(m.group(1)))
    return max_seq + 1


def generate_spawn_bag_ids(
    db: Session,
    sterilization_run_id: int,
    species_id: int,
    count: int,
) -> list[str]:
    """Generate `count` unique spawn bag IDs for the given sterilization run and species."""
    run = db.get(models.SterilizationRun, sterilization_run_id)
    if not run:
        raise ValueError(f"Sterilization run {sterilization_run_id} not found")
    species = db.get(models.MushroomSpecies, species_id)
    if not species:
        raise ValueError(f"Species {species_id} not found")
    recipe = db.get(models.SpawnRecipe, run.spawn_recipe_id)
    if not recipe:
        raise ValueError(f"Spawn recipe not found for run {sterilization_run_id}")

    run_code = _sanitize_run_code(run.run_code)
    recipe_code = recipe.recipe_code
    species_code = species.code
    stem = f"STER-{run_code}-{recipe_code}-{species_code}"

    ids = []
    start_seq = _next_seq_for_prefix(db, stem)
    for i in range(count):
        seq = start_seq + i
        ids.append(f"{stem}-{seq:04d}")
    return ids


def generate_substrate_bag_ids(
    db: Session,
    pasteurization_run_id: int,
    species_id: int,
    count: int,
) -> list[str]:
    """Generate `count` unique substrate bag IDs for the given pasteurization run and species."""
    run = db.get(models.PasteurizationRun, pasteurization_run_id)
    if not run:
        raise ValueError(f"Pasteurization run {pasteurization_run_id} not found")
    species = db.get(models.MushroomSpecies, species_id)
    if not species:
        raise ValueError(f"Species {species_id} not found")
    recipe = db.get(models.SubstrateRecipeVersion, run.substrate_recipe_version_id)
    if not recipe:
        raise ValueError(f"Substrate recipe not found for run {pasteurization_run_id}")

    run_code = _sanitize_run_code(run.run_code)
    recipe_code = recipe.recipe_code
    species_code = species.code
    stem = f"PAST-{run_code}-{recipe_code}-{species_code}"

    ids = []
    start_seq = _next_seq_for_prefix(db, stem)
    for i in range(count):
        seq = start_seq + i
        ids.append(f"{stem}-{seq:04d}")
    return ids


def _sanitize_run_code(run_code: str) -> str:
    """Replace spaces/special chars for use in bag ID."""
    return re.sub(r"[^A-Za-z0-9\-]", "-", run_code.strip())[:40]
