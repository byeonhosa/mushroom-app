"""
CRUD for reference / supporting entities: species, liquid cultures, grain types,
fill profiles, spawn/substrate recipes, mix lots, ingredients, and run records.
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from . import models


# --- Fill profiles ---

def list_fill_profiles(db: Session):
    return db.execute(select(models.FillProfile).order_by(models.FillProfile.fill_profile_id)).scalars().all()


def create_fill_profile(db: Session, name: str, dry: float, water: float, notes: str | None):
    fp = models.FillProfile(name=name, target_dry_kg_per_bag=dry, target_water_kg_per_bag=water, notes=notes)
    db.add(fp)
    db.commit()
    db.refresh(fp)
    return fp


# --- Substrate recipe versions ---

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


# --- Spawn recipes ---

def list_spawn_recipes(db: Session):
    return db.execute(select(models.SpawnRecipe).order_by(models.SpawnRecipe.spawn_recipe_id)).scalars().all()


def create_spawn_recipe(db: Session, data: dict):
    r = models.SpawnRecipe(**data)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


# --- Mix lots ---

def list_mix_lots(db: Session):
    return db.execute(select(models.MixLot).order_by(models.MixLot.mix_lot_id.desc())).scalars().all()


def create_mix_lot(db: Session, data: dict):
    m = models.MixLot(**data)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


# --- Species ---

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


# --- Liquid cultures ---

def list_liquid_cultures(db: Session, active_only: bool = True):
    stmt = (
        select(models.LiquidCulture)
        .options(joinedload(models.LiquidCulture.species))
        .order_by(models.LiquidCulture.culture_code.asc(), models.LiquidCulture.liquid_culture_id.asc())
    )
    if active_only:
        stmt = stmt.where(models.LiquidCulture.is_active.is_(True))
    return db.execute(stmt).scalars().all()


def create_liquid_culture(db: Session, data: dict):
    culture = models.LiquidCulture(**data)
    db.add(culture)
    db.commit()
    db.refresh(culture)
    return culture


# --- Grain types ---

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


# --- Ingredients ---

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
