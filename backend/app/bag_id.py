"""Bag identity generation for internal records and printable bag codes."""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models


def _next_seq_for_column(db: Session, column, prefix: str) -> int:
    """Find highest seq for values matching prefix-{seq} and return next."""
    sql_prefix = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"{sql_prefix}-%"
    rows = db.execute(select(column).where(column.like(pattern, escape="\\"))).scalars().all()
    max_seq = 0
    for value in rows:
        if not value:
            continue
        match = re.match(rf"^{re.escape(prefix)}-(\d+)$", value)
        if match:
            max_seq = max(max_seq, int(match.group(1)))
    return max_seq + 1


def generate_internal_bag_ids(db: Session, bag_type: str, count: int) -> list[str]:
    prefix = "SPNREC" if bag_type == "SPAWN" else "SUBREC"
    start_seq = _next_seq_for_column(db, models.Bag.bag_id, prefix)
    return [f"{prefix}-{start_seq + offset:04d}" for offset in range(count)]


def generate_spawn_bag_ids(
    db: Session,
    sterilization_run_id: int,
    species_id: int,
    count: int,
) -> list[str]:
    """Generate `count` unique printable spawn bag codes for the given run and species."""
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
    stem = f"STER-{run_code}-{recipe.recipe_code}-{species.code}"
    start_seq = _next_seq_for_column(db, models.Bag.bag_code, stem)
    return [f"{stem}-{start_seq + offset:04d}" for offset in range(count)]


def generate_substrate_bag_ids(
    db: Session,
    pasteurization_run_id: int,
    species_id: int,
    count: int,
) -> list[str]:
    """Generate `count` unique printable substrate bag codes for the given run and species."""
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
    stem = f"PAST-{run_code}-{recipe.recipe_code}-{species.code}"
    start_seq = _next_seq_for_column(db, models.Bag.bag_code, stem)
    return [f"{stem}-{start_seq + offset:04d}" for offset in range(count)]


def _sanitize_run_code(run_code: str) -> str:
    return re.sub(r"[^A-Za-z0-9\-]", "-", run_code.strip())[:40]
