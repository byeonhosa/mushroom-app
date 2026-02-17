from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
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
    ev = models.HarvestEvent(**data)
    db.add(ev); db.commit(); db.refresh(ev)
    return ev

def create_harvest_from_batch(db: Session, data: dict):
    substrate_batch_id = data["substrate_batch_id"]
    batch = db.get(models.SubstrateBatch, substrate_batch_id)
    if not batch:
        raise LookupError("Substrate batch not found")

    bag_id = str(substrate_batch_id)
    bag = db.get(models.SubstrateBag, bag_id)
    if not bag:
        bag = db.execute(
            select(models.SubstrateBag)
            .where(models.SubstrateBag.substrate_batch_id == substrate_batch_id)
            .order_by(models.SubstrateBag.bag_id.asc())
        ).scalars().first()
    if not bag:
        raise LookupError("No substrate bag found for substrate batch")

    harvest_event_data = {
        "bag_id": bag.bag_id,
        "flush_number": data["flush_number"],
        "fresh_weight_kg": data["harvested_kg"],
        "notes": data.get("notes"),
    }
    if data.get("harvested_at") is not None:
        harvest_event_data["harvested_at"] = data["harvested_at"]

    ev = create_harvest_event(db, harvest_event_data)
    return {
        "harvest_event_id": ev.harvest_event_id,
        "substrate_batch_id": substrate_batch_id,
        "bag_id": ev.bag_id,
        "flush_number": ev.flush_number,
        "harvested_kg": float(ev.fresh_weight_kg),
        "harvested_at": ev.harvested_at,
        "notes": ev.notes,
    }

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
