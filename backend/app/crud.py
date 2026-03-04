from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

from . import models
from . import bag_id


# --- Reference data ---

def list_fill_profiles(db: Session):
    return db.execute(select(models.FillProfile).order_by(models.FillProfile.fill_profile_id)).scalars().all()


def create_fill_profile(db: Session, name: str, dry: float, water: float, notes: str | None):
    fp = models.FillProfile(name=name, target_dry_kg_per_bag=dry, target_water_kg_per_bag=water, notes=notes)
    db.add(fp)
    db.commit()
    db.refresh(fp)
    return fp


def list_substrate_recipe_versions(db: Session):
    return db.execute(
        select(models.SubstrateRecipeVersion).order_by(models.SubstrateRecipeVersion.substrate_recipe_version_id)
    ).scalars().all()


def create_substrate_recipe_version(db: Session, data: dict):
    r = models.SubstrateRecipeVersion(**data)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def list_spawn_recipes(db: Session):
    return db.execute(select(models.SpawnRecipe).order_by(models.SpawnRecipe.spawn_recipe_id)).scalars().all()


def create_spawn_recipe(db: Session, data: dict):
    r = models.SpawnRecipe(**data)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def list_mix_lots(db: Session):
    return db.execute(select(models.MixLot).order_by(models.MixLot.mix_lot_id.desc())).scalars().all()


def create_mix_lot(db: Session, data: dict):
    m = models.MixLot(**data)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def list_species(db: Session, active_only: bool = True):
    stmt = select(models.MushroomSpecies).order_by(models.MushroomSpecies.name.asc(), models.MushroomSpecies.species_id.asc())
    if active_only:
        stmt = stmt.where(models.MushroomSpecies.is_active.is_(True))
    return db.execute(stmt).scalars().all()


def create_species(db: Session, data: dict):
    s = models.MushroomSpecies(**data)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def update_species(db: Session, species_id: int, data: dict):
    s = db.get(models.MushroomSpecies, species_id)
    if not s:
        return None
    for k, v in data.items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s


def list_grain_types(db: Session):
    return db.execute(
        select(models.GrainType).order_by(models.GrainType.name.asc(), models.GrainType.grain_type_id.asc())
    ).scalars().all()


def create_grain_type(db: Session, data: dict):
    g = models.GrainType(**data)
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


def update_grain_type(db: Session, grain_type_id: int, data: dict):
    g = db.get(models.GrainType, grain_type_id)
    if not g:
        return None
    for k, v in data.items():
        setattr(g, k, v)
    db.commit()
    db.refresh(g)
    return g


def list_ingredients(db: Session):
    return db.execute(
        select(models.Ingredient).order_by(models.Ingredient.name.asc(), models.Ingredient.ingredient_id.asc())
    ).scalars().all()


def create_ingredient(db: Session, data: dict):
    i = models.Ingredient(**data)
    db.add(i)
    db.commit()
    db.refresh(i)
    return i


def update_ingredient(db: Session, ingredient_id: int, data: dict):
    i = db.get(models.Ingredient, ingredient_id)
    if not i:
        return None
    for k, v in data.items():
        setattr(i, k, v)
    db.commit()
    db.refresh(i)
    return i


def list_ingredient_lots(db: Session, ingredient_id: int | None = None):
    stmt = select(models.IngredientLot).order_by(models.IngredientLot.ingredient_lot_id.desc())
    if ingredient_id is not None:
        stmt = stmt.where(models.IngredientLot.ingredient_id == ingredient_id)
    return db.execute(stmt).scalars().all()


def create_ingredient_lot(db: Session, data: dict):
    lot = models.IngredientLot(**data)
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot


# --- Pasteurization runs ---

def create_pasteurization_run(db: Session, data: dict):
    r = models.PasteurizationRun(**data)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def list_pasteurization_runs(db: Session):
    return db.execute(
        select(models.PasteurizationRun).order_by(models.PasteurizationRun.pasteurization_run_id.desc())
    ).scalars().all()


def get_pasteurization_run(db: Session, pasteurization_run_id: int):
    return db.get(models.PasteurizationRun, pasteurization_run_id)


def update_pasteurization_run(db: Session, pasteurization_run_id: int, data: dict):
    r = db.get(models.PasteurizationRun, pasteurization_run_id)
    if not r:
        return None
    for k, v in data.items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return r


# --- Sterilization runs ---

def create_sterilization_run(db: Session, data: dict):
    r = models.SterilizationRun(**data)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def list_sterilization_runs(
    db: Session,
    run_code_contains: str | None = None,
    sort_by: str = "sterilization_run_id",
    sort_order: str = "desc",
):
    stmt = select(models.SterilizationRun)
    if run_code_contains:
        stmt = stmt.where(models.SterilizationRun.run_code.ilike(f"%{run_code_contains}%"))
    sort_col = getattr(models.SterilizationRun, sort_by, models.SterilizationRun.sterilization_run_id)
    stmt = stmt.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    return db.execute(stmt).scalars().all()


def get_sterilization_run(db: Session, sterilization_run_id: int):
    return db.get(models.SterilizationRun, sterilization_run_id)


def update_sterilization_run(db: Session, sterilization_run_id: int, data: dict):
    r = db.get(models.SterilizationRun, sterilization_run_id)
    if not r:
        return None
    for k, v in data.items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return r


# --- Bags ---

def create_spawn_bags(db: Session, sterilization_run_id: int, species_id: int, bag_count: int) -> list[models.Bag]:
    ids = bag_id.generate_spawn_bag_ids(db, sterilization_run_id, species_id, bag_count)
    run = db.get(models.SterilizationRun, sterilization_run_id)
    species = db.get(models.MushroomSpecies, species_id)
    bags = []
    for bid in ids:
        bag = models.Bag(
            bag_id=bid,
            bag_type="SPAWN",
            species_id=species_id,
            sterilization_run_id=sterilization_run_id,
            pasteurization_run_id=None,
            mix_lot_id=None,
            substrate_recipe_version_id=None,
            spawn_recipe_id=run.spawn_recipe_id,
            grain_type_id=run.grain_type_id,
            status="FILLED",
        )
        db.add(bag)
        bags.append(bag)
    db.commit()
    for b in bags:
        db.refresh(b)
    return bags


def create_substrate_bags(db: Session, pasteurization_run_id: int, species_id: int, bag_count: int) -> list[models.Bag]:
    ids = bag_id.generate_substrate_bag_ids(db, pasteurization_run_id, species_id, bag_count)
    run = db.get(models.PasteurizationRun, pasteurization_run_id)
    species = db.get(models.MushroomSpecies, species_id)
    bags = []
    for bid in ids:
        bag = models.Bag(
            bag_id=bid,
            bag_type="SUBSTRATE",
            species_id=species_id,
            pasteurization_run_id=pasteurization_run_id,
            sterilization_run_id=None,
            mix_lot_id=run.mix_lot_id,
            substrate_recipe_version_id=run.substrate_recipe_version_id,
            spawn_recipe_id=None,
            grain_type_id=None,
            status="FILLED",
        )
        db.add(bag)
        bags.append(bag)
    db.commit()
    for b in bags:
        db.refresh(b)
    return bags


def get_bag(db: Session, bag_id: str) -> models.Bag | None:
    return db.get(models.Bag, bag_id)


def list_bags(
    db: Session,
    bag_type: str | None = None,
    species_id: int | None = None,
    pasteurization_run_id: int | None = None,
    sterilization_run_id: int | None = None,
    status: str | None = None,
    limit: int = 500,
):
    stmt = select(models.Bag)
    if bag_type:
        stmt = stmt.where(models.Bag.bag_type == bag_type)
    if species_id is not None:
        stmt = stmt.where(models.Bag.species_id == species_id)
    if pasteurization_run_id is not None:
        stmt = stmt.where(models.Bag.pasteurization_run_id == pasteurization_run_id)
    if sterilization_run_id is not None:
        stmt = stmt.where(models.Bag.sterilization_run_id == sterilization_run_id)
    if status:
        stmt = stmt.where(models.Bag.status == status)
    stmt = stmt.order_by(models.Bag.created_at.desc()).limit(max(1, min(limit, 1000)))
    return db.execute(stmt).scalars().all()


def get_bag_detail(db: Session, bag_id: str) -> models.Bag | None:
    bag = db.get(models.Bag, bag_id)
    if bag:
        _ = bag.harvest_events  # load
    return bag


def update_bag_incubation_start(db: Session, bag_id: str) -> models.Bag | None:
    bag = db.get(models.Bag, bag_id)
    if not bag:
        return None
    bag.incubation_start_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(bag)
    return bag


def update_bag_fruiting_start(db: Session, bag_id: str) -> models.Bag | None:
    bag = db.get(models.Bag, bag_id)
    if not bag:
        return None
    if bag.bag_type != "SUBSTRATE":
        raise ValueError("Only substrate bags can be moved to fruiting")
    bag.fruiting_start_at = datetime.now(timezone.utc)
    bag.status = "FRUITING"
    db.commit()
    db.refresh(bag)
    return bag


def update_bag_disposal(db: Session, bag_id: str, disposal_reason: str) -> models.Bag | None:
    bag = db.get(models.Bag, bag_id)
    if not bag:
        return None
    bag.disposed_at = datetime.now(timezone.utc)
    bag.disposal_reason = disposal_reason
    bag.status = "DISPOSED" if disposal_reason == "FINAL_HARVEST" else "CONTAMINATED"
    db.commit()
    db.refresh(bag)
    return bag


# --- Inoculations ---

def create_inoculation(db: Session, substrate_bag_id: str, spawn_bag_id: str, inoculated_at=None):
    sub = db.get(models.Bag, substrate_bag_id)
    if not sub:
        raise LookupError("Substrate bag not found")
    spawn = db.get(models.Bag, spawn_bag_id)
    if not spawn:
        raise LookupError("Spawn bag not found")
    if sub.bag_type != "SUBSTRATE":
        raise ValueError("Substrate bag must be SUBSTRATE type")
    if spawn.bag_type != "SPAWN":
        raise ValueError("Spawn bag must be SPAWN type")
    if spawn.status == "CONSUMED":
        raise ValueError("Spawn bag is already consumed")
    inoc = models.Inoculation(
        substrate_bag_id=substrate_bag_id,
        spawn_bag_id=spawn_bag_id,
        inoculated_at=inoculated_at or datetime.now(timezone.utc),
    )
    db.add(inoc)
    sub.inoculated_at = inoc.inoculated_at
    sub.parent_spawn_bag_id = spawn_bag_id
    sub.status = "INCUBATING"
    sub.incubation_start_at = inoc.inoculated_at  # Assume inoculation = into incubation tent
    spawn.consumed_at = inoc.inoculated_at
    spawn.status = "CONSUMED"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(inoc)
    return inoc


def get_inoculation_for_substrate_bag(db: Session, substrate_bag_id: str):
    return db.execute(
        select(models.Inoculation).where(models.Inoculation.substrate_bag_id == substrate_bag_id)
    ).scalar_one_or_none()


def list_substrate_bags_inoculated_by(db: Session, spawn_bag_id: str):
    inocs = db.execute(
        select(models.Inoculation).where(models.Inoculation.spawn_bag_id == spawn_bag_id)
    ).scalars().all()
    ids = [i.substrate_bag_id for i in inocs]
    if not ids:
        return []
    return db.execute(
        select(models.Bag).where(models.Bag.bag_id.in_(ids)).order_by(models.Bag.bag_id.asc())
    ).scalars().all()


# --- Harvest events ---

def create_harvest_event(db: Session, bag_id: str, flush_number: int, fresh_weight_kg: float, harvested_at=None, notes=None):
    bag = db.get(models.Bag, bag_id)
    if not bag:
        raise LookupError("Bag not found")
    if bag.bag_type != "SUBSTRATE":
        raise ValueError("Harvest events only for substrate bags")
    ev = models.HarvestEvent(
        bag_id=bag_id,
        flush_number=flush_number,
        fresh_weight_kg=fresh_weight_kg,
        harvested_at=harvested_at or datetime.now(timezone.utc),
        notes=notes,
    )
    db.add(ev)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(ev)
    return ev


def list_harvest_events_for_bag(db: Session, bag_id: str):
    return db.execute(
        select(models.HarvestEvent)
        .where(models.HarvestEvent.bag_id == bag_id)
        .order_by(models.HarvestEvent.flush_number.asc())
    ).scalars().all()


def get_bag_total_harvest_kg(db: Session, bag_id: str) -> float:
    row = db.execute(
        select(func.coalesce(func.sum(models.HarvestEvent.fresh_weight_kg), 0))
        .where(models.HarvestEvent.bag_id == bag_id)
    ).scalar_one()
    return float(row)
