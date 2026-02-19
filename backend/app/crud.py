from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
import re
from datetime import datetime, timezone
from . import models

IN_HOUSE_ONLY_SPAWN_FIELDS = (
    "sterilization_run_id",
    "grain_type_id",
    "grain_kg",
    "vermiculite_kg",
    "water_kg",
    "supplement_kg",
)

LEGACY_IN_HOUSE_ONLY_SPAWN_FIELDS = (
    "grain_dry_kg",
    "grain_water_kg",
    "lc_vendor",
    "lc_code",
    "sterilization_run_code",
    "incubation_zone_id",
)


def _normalize_spawn_batch_data(data: dict, existing: models.SpawnBatch | None = None) -> dict:
    normalized = dict(data)
    spawn_type = normalized.get("spawn_type", existing.spawn_type if existing else None)
    if spawn_type == models.SpawnType.PURCHASED_BLOCK.value:
        for field in IN_HOUSE_ONLY_SPAWN_FIELDS:
            normalized[field] = None
        for field in LEGACY_IN_HOUSE_ONLY_SPAWN_FIELDS:
            normalized[field] = None
    elif spawn_type == models.SpawnType.IN_HOUSE_GRAIN.value:
        effective = {
            "grain_type_id": normalized.get("grain_type_id", existing.grain_type_id if existing else None),
            "grain_kg": normalized.get("grain_kg", existing.grain_kg if existing else None),
            "vermiculite_kg": normalized.get("vermiculite_kg", existing.vermiculite_kg if existing else None),
            "water_kg": normalized.get("water_kg", existing.water_kg if existing else None),
        }
        missing = [name for name, value in effective.items() if value is None]
        if missing:
            raise ValueError(
                "IN_HOUSE_GRAIN requires grain_type_id, grain_kg, vermiculite_kg, water_kg. "
                f"Missing: {', '.join(missing)}"
            )
    return normalized

def _validate_spawn_batch_fk_refs(db: Session, data: dict):
    grain_type_id = data.get("grain_type_id")
    if grain_type_id is not None and not db.get(models.GrainType, grain_type_id):
        raise ValueError(f"Invalid grain_type_id: {grain_type_id}")

    sterilization_run_id = data.get("sterilization_run_id")
    if sterilization_run_id is not None and not db.get(models.SterilizationRun, sterilization_run_id):
        raise ValueError(f"Invalid sterilization_run_id: {sterilization_run_id}")

def _compute_spawn_recipe_metrics(spawn_batch: models.SpawnBatch):
    grain_kg = float(spawn_batch.grain_kg) if spawn_batch.grain_kg is not None else None
    vermiculite_kg = float(spawn_batch.vermiculite_kg) if spawn_batch.vermiculite_kg is not None else None
    water_kg = float(spawn_batch.water_kg) if spawn_batch.water_kg is not None else None
    supplement_kg = float(spawn_batch.supplement_kg) if spawn_batch.supplement_kg is not None else 0.0

    hydration_ratio = None
    expected_added_water_wb_pct = None
    if grain_kg is not None and vermiculite_kg is not None and water_kg is not None:
        dry_total = grain_kg + vermiculite_kg + supplement_kg
        if dry_total > 0:
            hydration_ratio = water_kg / dry_total
        total_with_water = dry_total + water_kg
        if total_with_water > 0:
            expected_added_water_wb_pct = (water_kg / total_with_water) * 100.0

    setattr(spawn_batch, "hydration_ratio", hydration_ratio)
    setattr(spawn_batch, "expected_added_water_wb_pct", expected_added_water_wb_pct)
    return spawn_batch

def _enrich_spawn_batch(spawn_batch: models.SpawnBatch):
    return _compute_spawn_recipe_metrics(spawn_batch)


def create_fill_profile(db: Session, name: str, dry: float, water: float, notes: str | None):
    fp = models.FillProfile(name=name, target_dry_kg_per_bag=dry, target_water_kg_per_bag=water, notes=notes)
    db.add(fp); db.commit(); db.refresh(fp)
    return fp

def list_fill_profiles(db: Session):
    return db.execute(select(models.FillProfile).order_by(models.FillProfile.fill_profile_id)).scalars().all()

def list_mix_lots(db: Session):
    return db.execute(select(models.MixLot).order_by(models.MixLot.mix_lot_id.desc())).scalars().all()

def create_mix_lot(db: Session, data: dict):
    item = models.MixLot(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

def list_spawn_recipes(db: Session):
    return db.execute(select(models.SpawnRecipe).order_by(models.SpawnRecipe.spawn_recipe_id.desc())).scalars().all()

def create_spawn_recipe(db: Session, data: dict):
    item = models.SpawnRecipe(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

def list_species(db: Session, active_only: bool = True):
    stmt = select(models.MushroomSpecies).order_by(models.MushroomSpecies.name.asc(), models.MushroomSpecies.species_id.asc())
    if active_only:
        stmt = stmt.where(models.MushroomSpecies.is_active.is_(True))
    return db.execute(stmt).scalars().all()

def create_species(db: Session, data: dict):
    item = models.MushroomSpecies(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

def update_species(db: Session, species_id: int, data: dict):
    item = db.get(models.MushroomSpecies, species_id)
    if not item:
        return None
    for k, v in data.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item

def list_grain_types(db: Session):
    return db.execute(
        select(models.GrainType).order_by(models.GrainType.name.asc(), models.GrainType.grain_type_id.asc())
    ).scalars().all()

def create_grain_type(db: Session, data: dict):
    grain_type = models.GrainType(**data)
    db.add(grain_type)
    db.commit()
    db.refresh(grain_type)
    return grain_type

def update_grain_type(db: Session, grain_type_id: int, data: dict):
    grain_type = db.get(models.GrainType, grain_type_id)
    if not grain_type:
        return None
    for k, v in data.items():
        setattr(grain_type, k, v)
    db.commit()
    db.refresh(grain_type)
    return grain_type

def create_sterilization_run(db: Session, data: dict):
    run = models.SterilizationRun(**data)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run

def list_sterilization_runs(
    db: Session,
    run_code_contains: str | None = None,
    unloaded_from=None,
    unloaded_to=None,
    sort_by: str = "sterilization_run_id",
    sort_order: str = "desc",
):
    stmt = select(models.SterilizationRun)

    if run_code_contains:
        stmt = stmt.where(models.SterilizationRun.run_code.ilike(f"%{run_code_contains}%"))
    if unloaded_from is not None:
        stmt = stmt.where(models.SterilizationRun.unloaded_at >= unloaded_from)
    if unloaded_to is not None:
        stmt = stmt.where(models.SterilizationRun.unloaded_at <= unloaded_to)

    sort_col = {
        "sterilization_run_id": models.SterilizationRun.sterilization_run_id,
        "run_code": models.SterilizationRun.run_code,
        "unloaded_at": models.SterilizationRun.unloaded_at,
    }.get(sort_by, models.SterilizationRun.sterilization_run_id)
    order_expr = sort_col.asc() if sort_order == "asc" else sort_col.desc()
    stmt = stmt.order_by(order_expr, models.SterilizationRun.sterilization_run_id.desc())
    return db.execute(stmt).scalars().all()

def get_sterilization_run(db: Session, sterilization_run_id: int):
    return db.get(models.SterilizationRun, sterilization_run_id)

def update_sterilization_run(db: Session, sterilization_run_id: int, data: dict):
    run = db.get(models.SterilizationRun, sterilization_run_id)
    if not run:
        return None
    for k, v in data.items():
        setattr(run, k, v)
    db.commit()
    db.refresh(run)
    return run

def list_ingredients(db: Session):
    return db.execute(
        select(models.Ingredient).order_by(models.Ingredient.name.asc(), models.Ingredient.ingredient_id.asc())
    ).scalars().all()

def create_ingredient(db: Session, data: dict):
    ingredient = models.Ingredient(**data)
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return ingredient

def update_ingredient(db: Session, ingredient_id: int, data: dict):
    ingredient = db.get(models.Ingredient, ingredient_id)
    if not ingredient:
        return None
    for k, v in data.items():
        setattr(ingredient, k, v)
    db.commit()
    db.refresh(ingredient)
    return ingredient

def list_ingredient_lots(db: Session, ingredient_id: int | None = None):
    stmt = (
        select(models.IngredientLot)
        .options(joinedload(models.IngredientLot.ingredient))
        .order_by(models.IngredientLot.ingredient_lot_id.desc())
    )
    if ingredient_id is not None:
        stmt = stmt.where(models.IngredientLot.ingredient_id == ingredient_id)
    return db.execute(stmt).scalars().all()

def _validate_block_refs(db: Session, data: dict):
    checks = (
        ("species_id", models.MushroomSpecies, "Invalid species_id: {}"),
        ("mix_lot_id", models.MixLot, "Invalid mix_lot_id: {}"),
        ("pasteurization_run_id", models.PasteurizationRun, "Invalid pasteurization_run_id: {}"),
        ("sterilization_run_id", models.SterilizationRun, "Invalid sterilization_run_id: {}"),
        ("spawn_recipe_id", models.SpawnRecipe, "Invalid spawn_recipe_id: {}"),
        ("substrate_batch_id", models.SubstrateBatch, "Invalid substrate_batch_id: {}"),
        ("spawn_batch_id", models.SpawnBatch, "Invalid spawn_batch_id: {}"),
    )
    for key, model, msg in checks:
        value = data.get(key)
        if value is not None and not db.get(model, value):
            raise ValueError(msg.format(value))

def _generate_block_code(db: Session, block_type: str) -> str:
    prefix = "SP" if block_type == "SPAWN" else "SB"
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    stem = f"{prefix}-{day}-"
    pattern = f"{stem}%"
    rows = db.execute(
        select(models.Block.block_code).where(models.Block.block_code.like(pattern))
    ).scalars().all()
    max_seq = 0
    for code in rows:
        m = re.match(rf"^{re.escape(stem)}(\d{{4}})$", code or "")
        if m:
            max_seq = max(max_seq, int(m.group(1)))
    return f"{stem}{max_seq + 1:04d}"

def create_block(db: Session, data: dict):
    payload = dict(data)
    block_type = payload["block_type"]
    if block_type not in ("SPAWN", "SUBSTRATE"):
        raise ValueError("block_type must be SPAWN or SUBSTRATE")
    if payload.get("species_id") is None:
        raise ValueError("species_id is required")
    _validate_block_refs(db, payload)
    if block_type == "SPAWN":
        payload["mix_lot_id"] = None
        payload["pasteurization_run_id"] = None
    else:
        payload["sterilization_run_id"] = None
    payload["block_code"] = payload.get("block_code") or _generate_block_code(db, block_type)
    block = models.Block(**payload)
    db.add(block)
    db.commit()
    db.refresh(block)
    return block

def list_blocks(
    db: Session,
    block_type: str | None = None,
    species_id: int | None = None,
    mix_lot_id: int | None = None,
    pasteurization_run_id: int | None = None,
    sterilization_run_id: int | None = None,
    limit: int = 200,
):
    stmt = select(models.Block)
    if block_type:
        stmt = stmt.where(models.Block.block_type == block_type)
    if species_id is not None:
        stmt = stmt.where(models.Block.species_id == species_id)
    if mix_lot_id is not None:
        stmt = stmt.where(models.Block.mix_lot_id == mix_lot_id)
    if pasteurization_run_id is not None:
        stmt = stmt.where(models.Block.pasteurization_run_id == pasteurization_run_id)
    if sterilization_run_id is not None:
        stmt = stmt.where(models.Block.sterilization_run_id == sterilization_run_id)
    stmt = stmt.order_by(models.Block.block_id.desc()).limit(max(1, min(limit, 1000)))
    return db.execute(stmt).scalars().all()

def get_block(db: Session, block_id: int):
    return db.get(models.Block, block_id)

def list_blocks_for_substrate_batch(db: Session, substrate_batch_id: int):
    return db.execute(
        select(models.Block)
        .where(models.Block.substrate_batch_id == substrate_batch_id)
        .order_by(models.Block.block_id.desc())
    ).scalars().all()

def list_blocks_for_spawn_batch(db: Session, spawn_batch_id: int):
    return db.execute(
        select(models.Block)
        .where(models.Block.spawn_batch_id == spawn_batch_id)
        .order_by(models.Block.block_id.desc())
    ).scalars().all()

def create_inoculation(db: Session, data: dict):
    child = db.get(models.Block, data["child_block_id"])
    if not child:
        raise LookupError("Child block not found")
    parent = db.get(models.Block, data["parent_spawn_block_id"])
    if not parent:
        raise LookupError("Parent spawn block not found")
    if child.block_type != "SUBSTRATE":
        raise ValueError("child_block_id must reference a SUBSTRATE block")
    if parent.block_type != "SPAWN":
        raise ValueError("parent_spawn_block_id must reference a SPAWN block")
    inoc = models.Inoculation(**data)
    db.add(inoc)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(inoc)
    return {
        "inoculation_id": inoc.inoculation_id,
        "child_block_id": inoc.child_block_id,
        "parent_spawn_block_id": inoc.parent_spawn_block_id,
        "inoculated_at": inoc.inoculated_at,
        "notes": inoc.notes,
        "child_block_code": child.block_code,
        "parent_spawn_block_code": parent.block_code,
    }

def get_inoculation_for_child_block(db: Session, block_id: int):
    inoc = db.execute(
        select(models.Inoculation).where(models.Inoculation.child_block_id == block_id)
    ).scalar_one_or_none()
    if not inoc:
        return None
    child = db.get(models.Block, inoc.child_block_id)
    parent = db.get(models.Block, inoc.parent_spawn_block_id)
    return {
        "inoculation_id": inoc.inoculation_id,
        "child_block_id": inoc.child_block_id,
        "parent_spawn_block_id": inoc.parent_spawn_block_id,
        "inoculated_at": inoc.inoculated_at,
        "notes": inoc.notes,
        "child_block_code": child.block_code if child else None,
        "parent_spawn_block_code": parent.block_code if parent else None,
    }

def list_children_for_spawn_block(db: Session, spawn_block_id: int):
    inocs = db.execute(
        select(models.Inoculation).where(models.Inoculation.parent_spawn_block_id == spawn_block_id)
        .order_by(models.Inoculation.inoculation_id.desc())
    ).scalars().all()
    child_ids = [i.child_block_id for i in inocs]
    if not child_ids:
        return []
    blocks = db.execute(
        select(models.Block).where(models.Block.block_id.in_(child_ids)).order_by(models.Block.block_id.desc())
    ).scalars().all()
    return blocks

def create_ingredient_lot(db: Session, data: dict):
    ingredient_lot = models.IngredientLot(**data)
    db.add(ingredient_lot)
    db.commit()
    db.refresh(ingredient_lot)
    return db.execute(
        select(models.IngredientLot)
        .options(joinedload(models.IngredientLot.ingredient))
        .where(models.IngredientLot.ingredient_lot_id == ingredient_lot.ingredient_lot_id)
    ).scalar_one()

def update_ingredient_lot(db: Session, ingredient_lot_id: int, data: dict):
    ingredient_lot = db.get(models.IngredientLot, ingredient_lot_id)
    if not ingredient_lot:
        return None
    for k, v in data.items():
        setattr(ingredient_lot, k, v)
    db.commit()
    return db.execute(
        select(models.IngredientLot)
        .options(joinedload(models.IngredientLot.ingredient))
        .where(models.IngredientLot.ingredient_lot_id == ingredient_lot_id)
    ).scalar_one()

def create_spawn_batch(db: Session, data: dict):
    normalized = _normalize_spawn_batch_data(data)
    _validate_spawn_batch_fk_refs(db, normalized)
    spawn_batch = models.SpawnBatch(**normalized)
    db.add(spawn_batch)
    db.commit()
    db.refresh(spawn_batch)
    return _enrich_spawn_batch(spawn_batch)

def list_spawn_batches(
    db: Session,
    spawn_type: str | None = None,
    strain_contains: str | None = None,
    grain_type_id: int | None = None,
    sterilization_run_id: int | None = None,
    sort_by: str = "spawn_batch_id",
    sort_order: str = "desc",
):
    stmt = select(models.SpawnBatch)
    if spawn_type:
        stmt = stmt.where(models.SpawnBatch.spawn_type == spawn_type)
    if strain_contains:
        stmt = stmt.where(models.SpawnBatch.strain_code.ilike(f"%{strain_contains}%"))
    if grain_type_id is not None:
        stmt = stmt.where(models.SpawnBatch.grain_type_id == grain_type_id)
    if sterilization_run_id is not None:
        stmt = stmt.where(models.SpawnBatch.sterilization_run_id == sterilization_run_id)

    sort_col = {
        "spawn_batch_id": models.SpawnBatch.spawn_batch_id,
        "made_at": models.SpawnBatch.made_at,
        "incubation_start_at": models.SpawnBatch.incubation_start_at,
        "strain_code": models.SpawnBatch.strain_code,
    }.get(sort_by, models.SpawnBatch.spawn_batch_id)
    order_expr = sort_col.asc() if sort_order == "asc" else sort_col.desc()
    stmt = stmt.order_by(order_expr, models.SpawnBatch.spawn_batch_id.desc())
    rows = db.execute(stmt).scalars().all()
    return [_enrich_spawn_batch(row) for row in rows]

def update_spawn_batch(db: Session, spawn_batch_id: int, data: dict):
    spawn_batch = db.get(models.SpawnBatch, spawn_batch_id)
    if not spawn_batch:
        return None
    normalized = _normalize_spawn_batch_data(data, spawn_batch)
    _validate_spawn_batch_fk_refs(db, normalized)
    for k, v in normalized.items():
        setattr(spawn_batch, k, v)
    db.commit()
    db.refresh(spawn_batch)
    return _enrich_spawn_batch(spawn_batch)

def create_substrate_batch(db: Session, data: dict):
    batch = models.SubstrateBatch(**data)
    db.add(batch)
    db.commit()
    db.refresh(batch)

    for i in range(1, batch.bag_count + 1):
        bag_id = f"{batch.name}-{i:04d}"
        db.add(models.SubstrateBag(bag_id=bag_id, substrate_batch_id=batch.substrate_batch_id))
    db.commit()
    return db.get(models.SubstrateBatch, batch.substrate_batch_id)

def create_batch_inoculation(db: Session, data: dict):
    inoc = models.BatchInoculation(**data)
    db.add(inoc)
    db.commit()
    db.refresh(inoc)
    inoc = db.execute(
        select(models.BatchInoculation)
        .options(joinedload(models.BatchInoculation.spawn_batch))
        .where(models.BatchInoculation.batch_inoculation_id == inoc.batch_inoculation_id)
    ).scalar_one()
    _enrich_spawn_batch(inoc.spawn_batch)
    return inoc

def list_batch_inoculations(db: Session, substrate_batch_id: int | None = None):
    stmt = (
        select(models.BatchInoculation)
        .options(joinedload(models.BatchInoculation.spawn_batch))
        .order_by(models.BatchInoculation.batch_inoculation_id.desc())
    )
    if substrate_batch_id is not None:
        stmt = stmt.where(models.BatchInoculation.substrate_batch_id == substrate_batch_id)
    rows = db.execute(stmt).scalars().all()
    for row in rows:
        _enrich_spawn_batch(row.spawn_batch)
    return rows

def get_batch_inoculation_for_batch(db: Session, substrate_batch_id: int):
    row = db.execute(
        select(models.BatchInoculation)
        .options(joinedload(models.BatchInoculation.spawn_batch))
        .where(models.BatchInoculation.substrate_batch_id == substrate_batch_id)
    ).scalar_one_or_none()
    if row:
        _enrich_spawn_batch(row.spawn_batch)
    return row

def update_batch_inoculation(db: Session, batch_inoculation_id: int, data: dict):
    inoc = db.get(models.BatchInoculation, batch_inoculation_id)
    if not inoc:
        return None
    for k, v in data.items():
        setattr(inoc, k, v)
    db.commit()
    inoc = db.execute(
        select(models.BatchInoculation)
        .options(joinedload(models.BatchInoculation.spawn_batch))
        .where(models.BatchInoculation.batch_inoculation_id == batch_inoculation_id)
    ).scalar_one()
    _enrich_spawn_batch(inoc.spawn_batch)
    return inoc

def create_pasteurization_run(db: Session, data: dict):
    run = models.PasteurizationRun(**data)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run

def list_pasteurization_runs(db: Session):
    return db.execute(
        select(models.PasteurizationRun).order_by(models.PasteurizationRun.pasteurization_run_id.desc())
    ).scalars().all()

def get_pasteurization_run(db: Session, pasteurization_run_id: int):
    return db.get(models.PasteurizationRun, pasteurization_run_id)

def update_pasteurization_run(db: Session, pasteurization_run_id: int, data: dict):
    run = db.get(models.PasteurizationRun, pasteurization_run_id)
    if not run:
        return None
    for k, v in data.items():
        setattr(run, k, v)
    db.commit()
    db.refresh(run)
    return run

def list_batches(db: Session):
    return db.execute(select(models.SubstrateBatch).order_by(models.SubstrateBatch.substrate_batch_id.desc())).scalars().all()

def get_bags_for_batch(db: Session, substrate_batch_id: int):
    return db.execute(
        select(models.SubstrateBag).where(models.SubstrateBag.substrate_batch_id == substrate_batch_id).order_by(models.SubstrateBag.bag_id)
    ).scalars().all()

def _get_batch_base_dry_kg(db: Session, substrate_batch_id: int) -> float:
    batch = db.execute(
        select(models.SubstrateBatch)
        .options(joinedload(models.SubstrateBatch.fill_profile))
        .where(models.SubstrateBatch.substrate_batch_id == substrate_batch_id)
    ).scalar_one_or_none()
    if not batch:
        raise LookupError("Substrate batch not found")
    return float(batch.bag_count) * float(batch.fill_profile.target_dry_kg_per_bag)

def _resolve_addin_amounts(base_dry_kg: float, dry_kg: float | None, pct_of_base_dry: float | None) -> tuple[float, float]:
    if dry_kg is None and pct_of_base_dry is None:
        raise ValueError("Either dry_kg or pct_of_base_dry is required")

    if dry_kg is None:
        return (base_dry_kg * (pct_of_base_dry / 100.0), pct_of_base_dry)
    if pct_of_base_dry is None:
        if base_dry_kg <= 0:
            if abs(dry_kg) > 1e-12:
                raise ValueError("Cannot infer percent from dry_kg when base_dry_kg is zero")
            return (0.0, 0.0)
        return (dry_kg, (dry_kg / base_dry_kg) * 100.0)

    expected_dry = base_dry_kg * (pct_of_base_dry / 100.0)
    if abs(expected_dry) <= 1e-12:
        if abs(dry_kg) > 1e-12:
            raise ValueError("Provided dry_kg and pct_of_base_dry do not agree")
    else:
        rel_err = abs(dry_kg - expected_dry) / abs(expected_dry)
        if rel_err > 0.005:
            raise ValueError("Provided dry_kg and pct_of_base_dry disagree by more than 0.5%")
    return (dry_kg, pct_of_base_dry)

def list_substrate_batch_addins(db: Session, substrate_batch_id: int):
    return db.execute(
        select(models.SubstrateBatchAddin)
        .options(joinedload(models.SubstrateBatchAddin.ingredient_lot).joinedload(models.IngredientLot.ingredient))
        .where(models.SubstrateBatchAddin.substrate_batch_id == substrate_batch_id)
        .order_by(models.SubstrateBatchAddin.substrate_batch_addin_id.asc())
    ).scalars().all()

def create_substrate_batch_addin(db: Session, substrate_batch_id: int, data: dict):
    base_dry_kg = _get_batch_base_dry_kg(db, substrate_batch_id)
    ingredient_lot = db.get(models.IngredientLot, data["ingredient_lot_id"])
    if not ingredient_lot:
        raise LookupError("Ingredient lot not found")

    dry_kg, pct_of_base_dry = _resolve_addin_amounts(
        base_dry_kg=base_dry_kg,
        dry_kg=data.get("dry_kg"),
        pct_of_base_dry=data.get("pct_of_base_dry"),
    )
    addin = models.SubstrateBatchAddin(
        substrate_batch_id=substrate_batch_id,
        ingredient_lot_id=data["ingredient_lot_id"],
        dry_kg=dry_kg,
        pct_of_base_dry=pct_of_base_dry,
        notes=data.get("notes"),
    )
    db.add(addin)
    db.commit()
    db.refresh(addin)
    return db.execute(
        select(models.SubstrateBatchAddin)
        .options(joinedload(models.SubstrateBatchAddin.ingredient_lot).joinedload(models.IngredientLot.ingredient))
        .where(models.SubstrateBatchAddin.substrate_batch_addin_id == addin.substrate_batch_addin_id)
    ).scalar_one()

def delete_substrate_batch_addin(db: Session, substrate_batch_id: int, substrate_batch_addin_id: int):
    addin = db.execute(
        select(models.SubstrateBatchAddin)
        .where(
            models.SubstrateBatchAddin.substrate_batch_addin_id == substrate_batch_addin_id,
            models.SubstrateBatchAddin.substrate_batch_id == substrate_batch_id,
        )
    ).scalar_one_or_none()
    if not addin:
        return False
    db.delete(addin)
    db.commit()
    return True

def get_bag_detail(db: Session, bag_id: str):
    bag = db.get(models.SubstrateBag, bag_id)
    if not bag:
        return None
    _ = bag.harvest_events
    return bag

def create_harvest_event(db: Session, data: dict):
    block = db.get(models.Block, data["block_id"])
    if not block:
        raise LookupError("Block not found")
    if block.block_type != "SUBSTRATE":
        raise ValueError("Harvest events can only be recorded for SUBSTRATE blocks")

    bag_id = None
    if block.substrate_batch_id is not None:
        bag = db.execute(
            select(models.SubstrateBag)
            .where(models.SubstrateBag.substrate_batch_id == block.substrate_batch_id)
            .order_by(models.SubstrateBag.bag_id.asc())
        ).scalars().first()
        bag_id = bag.bag_id if bag else None

    ev = models.HarvestEvent(
        block_id=block.block_id,
        bag_id=bag_id,
        flush_number=data["flush_number"],
        fresh_weight_kg=data["fresh_weight_kg"],
        harvested_at=data.get("harvested_at"),
        notes=data.get("notes"),
    )
    db.add(ev); db.commit(); db.refresh(ev)
    return ev

def list_harvest_events_for_block(db: Session, block_id: int):
    return db.execute(
        select(models.HarvestEvent)
        .where(models.HarvestEvent.block_id == block_id)
        .order_by(models.HarvestEvent.harvested_at.desc(), models.HarvestEvent.harvest_event_id.desc())
    ).scalars().all()

def batch_metrics(db: Session, substrate_batch_id: int):
    batch = db.get(models.SubstrateBatch, substrate_batch_id)
    if not batch:
        return None

    total_harvest = db.execute(
        select(func.coalesce(func.sum(models.HarvestEvent.fresh_weight_kg), 0))
        .join(models.SubstrateBag, models.SubstrateBag.bag_id == models.HarvestEvent.bag_id)
        .where(models.SubstrateBag.substrate_batch_id == substrate_batch_id)
    ).scalar_one()

    dry_per_bag = float(batch.fill_profile.target_dry_kg_per_bag)
    dry_total = dry_per_bag * batch.bag_count
    be = (float(total_harvest) / dry_total * 100.0) if dry_total > 0 else 0.0

    return {
        "substrate_batch_id": substrate_batch_id,
        "total_harvest_kg": float(total_harvest),
        "dry_kg_total": float(dry_total),
        "be_percent": float(be),
    }
