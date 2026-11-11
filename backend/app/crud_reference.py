"""
CRUD for reference / supporting entities: species, liquid cultures, grain types,
fill profiles, spawn/substrate recipes, mix lots, ingredients, and run records.
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, select

from . import models
from .errors import ConflictError, DomainError, NotFoundError

# Columns a run list may be sorted by (RUN-8). Anything else is refused.
STERILIZATION_RUN_SORT_FIELDS = (
    "sterilization_run_id",
    "run_code",
    "unloaded_at",
    "cycle_start_at",
    "cycle_end_at",
    "bag_count",
)


# --- Fill profiles ---

def _update_reference_row(db: Session, model, row_id: int, data: dict, *, keep_when_null: tuple[str, ...]):
    """Change the given fields of one reference row (REF-3 to REF-7, REF-14).

    A null for a field that must have a value means "leave it as it is".
    Nothing is ever deleted: `is_active` false takes the row out of the pick
    lists for new work, and the records that used it keep showing it.
    """
    row = db.get(model, row_id)
    if row is None:
        return None
    for key, value in data.items():
        if value is None and key in keep_when_null:
            continue
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def _usable(db: Session, model, row_id, what: str):
    """The reference row a new record is about to use: it must exist and be active."""
    row = db.get(model, row_id) if row_id is not None else None
    if row is None:
        raise NotFoundError(f"{what} not found")
    if not row.is_active:
        raise DomainError(f"That {what.lower()} is deactivated. Reactivate it, or choose another.")
    return row


def list_fill_profiles(db: Session):
    return db.execute(select(models.FillProfile).order_by(models.FillProfile.fill_profile_id)).scalars().all()


def create_fill_profile(db: Session, name: str, dry: float, water: float, notes: str | None):
    fp = models.FillProfile(name=name, target_dry_kg_per_bag=dry, target_water_kg_per_bag=water, notes=notes)
    db.add(fp)
    db.commit()
    db.refresh(fp)
    return fp


def update_fill_profile(db: Session, fill_profile_id: int, data: dict):
    return _update_reference_row(
        db,
        models.FillProfile,
        fill_profile_id,
        data,
        keep_when_null=("name", "target_dry_kg_per_bag", "target_water_kg_per_bag", "is_active"),
    )


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


def update_substrate_recipe_version(db: Session, recipe_id: int, data: dict):
    return _update_reference_row(
        db, models.SubstrateRecipeVersion, recipe_id, data, keep_when_null=("name", "recipe_code", "is_active")
    )


# --- Spawn recipes ---

def list_spawn_recipes(db: Session):
    return db.execute(select(models.SpawnRecipe).order_by(models.SpawnRecipe.spawn_recipe_id)).scalars().all()


def create_spawn_recipe(db: Session, data: dict):
    r = models.SpawnRecipe(**data)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def update_spawn_recipe(db: Session, spawn_recipe_id: int, data: dict):
    return _update_reference_row(
        db, models.SpawnRecipe, spawn_recipe_id, data, keep_when_null=("recipe_code", "is_active")
    )


# --- Mix lots ---

def list_mix_lots(db: Session):
    return db.execute(select(models.MixLot).order_by(models.MixLot.mix_lot_id.desc())).scalars().all()


def create_mix_lot(db: Session, data: dict):
    _usable(db, models.SubstrateRecipeVersion, data.get("substrate_recipe_version_id"), "Substrate recipe")
    _usable(db, models.FillProfile, data.get("fill_profile_id"), "Fill profile")
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


def _slug_in_use(db: Session, slug: str, *, except_species_id: int | None = None) -> bool:
    stmt = select(models.MushroomSpecies.species_id).where(models.MushroomSpecies.slug == slug)
    if except_species_id is not None:
        stmt = stmt.where(models.MushroomSpecies.species_id != except_species_id)
    return db.execute(stmt).first() is not None


def create_species(db: Session, data: dict):
    from .schemas import slugify

    data = dict(data)
    slug = data.get("slug") or slugify(data["name"])
    if not slug:
        raise DomainError("Give the species a name with at least one letter or digit.")
    if _slug_in_use(db, slug):
        raise ConflictError(f"Another species already uses the slug '{slug}'.")
    data["slug"] = slug
    s = models.MushroomSpecies(**data)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def update_species(db: Session, species_id: int, data: dict):
    s = db.get(models.MushroomSpecies, species_id)
    if not s:
        return None
    data = dict(data)
    if "slug" in data:
        new_slug = data.pop("slug")
        if new_slug is not None and new_slug != s.slug:
            # The website keys its species pages on the slug (brief section 10).
            if s.slug is not None:
                raise DomainError(
                    f"The slug '{s.slug}' is shared with the website and cannot be changed once set."
                )
            if _slug_in_use(db, new_slug, except_species_id=species_id):
                raise ConflictError(f"Another species already uses the slug '{new_slug}'.")
            s.slug = new_slug
    for required in ("name", "code", "sale_path", "in_rotation_now", "is_active"):
        if required in data and data[required] is None:
            data.pop(required)
    for k, v in data.items():
        setattr(s, k, v)
    if s.profile is not None:
        # The profile repeats the species' name for the reference page.
        s.profile.common_name = s.name
        s.profile.scientific_name = s.latin_name
    db.commit()
    db.refresh(s)
    return s


# --- Species profiles (read-only cultivation reference) ---

def list_species_profiles(db: Session):
    return db.execute(
        select(models.SpeciesProfile)
        .options(joinedload(models.SpeciesProfile.species))
        .order_by(models.SpeciesProfile.common_name.asc(), models.SpeciesProfile.species_profile_id.asc())
    ).scalars().all()


def get_species_profile(db: Session, code: str):
    """Find a profile by its species' slug (lion-s-mane) or label code (LM)."""
    return db.execute(
        select(models.SpeciesProfile)
        .join(models.MushroomSpecies)
        .options(joinedload(models.SpeciesProfile.species))
        .where((models.SpeciesProfile.code == code.lower()) | (models.MushroomSpecies.code == code.upper()))
    ).scalar_one_or_none()


# --- Liquid cultures ---

def list_liquid_cultures(db: Session, active_only: bool = True):
    stmt = (
        select(models.LiquidCulture)
        .options(joinedload(models.LiquidCulture.species), joinedload(models.LiquidCulture.parent))
        .order_by(models.LiquidCulture.culture_code.asc(), models.LiquidCulture.liquid_culture_id.asc())
    )
    if active_only:
        stmt = stmt.where(models.LiquidCulture.is_active.is_(True))
    return db.execute(stmt).scalars().all()


def _check_culture_parent(db: Session, culture_id: int | None, species_id: int, parent_id: int) -> None:
    """A parent must exist, be of the same species, and not descend from the culture itself (REF-12)."""
    parent = db.get(models.LiquidCulture, parent_id)
    if parent is None:
        raise NotFoundError("Parent culture not found")
    if parent.species_id != species_id:
        raise DomainError("A culture's parent must be of the same species.")
    seen: set[int] = set()
    node = parent
    while node is not None and node.liquid_culture_id not in seen:
        if node.liquid_culture_id == culture_id:
            raise DomainError("A culture cannot be made from itself or from one of its own descendants.")
        seen.add(node.liquid_culture_id)
        node = node.parent


def create_liquid_culture(db: Session, data: dict):
    if db.get(models.MushroomSpecies, data.get("species_id")) is None:
        raise NotFoundError("Species not found")
    if data.get("parent_liquid_culture_id") is not None:
        _check_culture_parent(db, None, data["species_id"], data["parent_liquid_culture_id"])
    culture = models.LiquidCulture(**data)
    db.add(culture)
    db.commit()
    db.refresh(culture)
    return culture


def update_liquid_culture(db: Session, liquid_culture_id: int, data: dict):
    culture = db.get(models.LiquidCulture, liquid_culture_id)
    if culture is None:
        return None
    if data.get("parent_liquid_culture_id") is not None:
        _check_culture_parent(db, culture.liquid_culture_id, culture.species_id, data["parent_liquid_culture_id"])
    for key, value in data.items():
        if value is None and key == "is_active":
            continue
        setattr(culture, key, value)
    db.commit()
    db.refresh(culture)
    return culture


# --- Purchased spawn lots (REF-11) ---

def list_purchased_spawn_lots(db: Session, *, usable_only: bool = False):
    """Newest first. `usable_only` leaves out lots that are deactivated or used up."""
    stmt = (
        select(models.PurchasedSpawnLot)
        .options(joinedload(models.PurchasedSpawnLot.species), joinedload(models.PurchasedSpawnLot.grain_type))
        .order_by(models.PurchasedSpawnLot.received_at.desc(), models.PurchasedSpawnLot.purchased_spawn_lot_id.desc())
    )
    if usable_only:
        stmt = stmt.where(
            models.PurchasedSpawnLot.is_active.is_(True), models.PurchasedSpawnLot.used_up_at.is_(None)
        )
    return db.execute(stmt).scalars().all()


def get_purchased_spawn_lot(db: Session, lot_id: int):
    return db.get(models.PurchasedSpawnLot, lot_id)


def _next_purchased_lot_code(db: Session, species_code: str, received_at) -> str:
    """PL-LM-261105A: purchased lot, species, the day it arrived, a letter for that day."""
    import string

    from .bag_id import farm_date

    stem = f"PL-{species_code}-{farm_date(received_at).strftime('%y%m%d')}"
    used = set(
        db.execute(
            select(models.PurchasedSpawnLot.lot_code).where(models.PurchasedSpawnLot.lot_code.like(f"{stem}_"))
        ).scalars().all()
    )
    for letter in string.ascii_uppercase:
        if f"{stem}{letter}" not in used:
            return f"{stem}{letter}"
    raise ConflictError("Too many lots of that species were received on that day.")


def create_purchased_spawn_lot(db: Session, data: dict):
    data = dict(data)
    # The species row is locked until commit, so two people recording a lot of
    # the same species at the same moment are given different letters.
    species = db.execute(
        select(models.MushroomSpecies)
        .where(models.MushroomSpecies.species_id == data.get("species_id"))
        .with_for_update()
    ).scalar_one_or_none()
    if species is None:
        raise NotFoundError("Species not found")
    if not species.is_active:
        raise DomainError(f"{species.name} is deactivated. Reactivate it before recording a lot of it.")
    if data.get("grain_type_id") is not None and db.get(models.GrainType, data["grain_type_id"]) is None:
        raise NotFoundError("Grain type not found")
    data["lot_code"] = _next_purchased_lot_code(db, species.code, data["received_at"])
    lot = models.PurchasedSpawnLot(**data)
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot


def update_purchased_spawn_lot(db: Session, lot_id: int, data: dict):
    from .crud_status import _now

    lot = db.get(models.PurchasedSpawnLot, lot_id)
    if lot is None:
        return None
    data = dict(data)
    if "used_up" in data:
        used_up = data.pop("used_up")
        if used_up is True and lot.used_up_at is None:
            lot.used_up_at = _now()
        elif used_up is False:
            lot.used_up_at = None
    if "species_id" in data and data["species_id"] != lot.species_id:
        in_use = db.execute(
            select(models.Bag.bag_id).where(models.Bag.source_purchased_spawn_lot_id == lot_id).limit(1)
        ).first()
        if in_use:
            raise DomainError("This lot has already inoculated bags, so its species cannot be changed.")
        if db.get(models.MushroomSpecies, data["species_id"]) is None:
            raise NotFoundError("Species not found")
    if data.get("grain_type_id") is not None and db.get(models.GrainType, data["grain_type_id"]) is None:
        raise NotFoundError("Grain type not found")
    for required in ("vendor", "species_id", "received_at", "is_active"):
        if required in data and data[required] is None:
            data.pop(required)
    for key, value in data.items():
        setattr(lot, key, value)
    db.commit()
    db.refresh(lot)
    return lot


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
    return _update_reference_row(db, models.GrainType, grain_type_id, data, keep_when_null=("name", "is_active"))


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
    return _update_reference_row(db, models.Ingredient, ingredient_id, data, keep_when_null=("name", "is_active"))


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
    if db.get(models.MixLot, data.get("mix_lot_id")) is None:
        raise NotFoundError("Mix lot not found")
    _usable(db, models.SubstrateRecipeVersion, data.get("substrate_recipe_version_id"), "Substrate recipe")
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


def _correct_run(
    db: Session,
    run,
    bag_run_column,
    data: dict,
    *,
    label: str,
    times: tuple[str, str],
    fixed_once_bags_exist: tuple[str, ...],
    keep_when_null: tuple[str, ...],
):
    """Apply a correction to a run (RUN-5), refusing what would falsify its bags.

    A run's bags copy its recipe when their records are created and print its
    code when they are labelled. So: the recipe, grain and mix lot can change
    only while the run has no bag records; the run code only while none of
    its bags has a label; and the planned count can never drop below the
    records that exist, nor cross 100 once labels exist, because that changes
    how many digits the bag number is printed with.
    """
    from .crud_status import _as_utc

    data = {key: value for key, value in data.items() if not (value is None and key in keep_when_null)}
    bag_filter = bag_run_column == getattr(run, bag_run_column.key)
    records = db.execute(select(func.count()).select_from(models.Bag).where(bag_filter)).scalar_one()
    labelled = db.execute(
        select(func.count()).select_from(models.Bag).where(bag_filter, models.Bag.bag_code.is_not(None))
    ).scalar_one()

    changed = {key: value for key, value in data.items() if getattr(run, key) != value}
    for key in fixed_once_bags_exist:
        if key in changed and records:
            raise DomainError(
                f"{label} already has {records} bag record(s) made with its recipe. "
                "The recipe, grain and mix lot cannot be changed now."
            )
    if "run_code" in changed and labelled:
        raise DomainError(
            f"The run code is printed on {labelled} bag label(s) and cannot be changed now."
        )
    if "bag_count" in changed:
        if changed["bag_count"] < records:
            raise DomainError(
                f"{label} already has {records} bag record(s); the planned count cannot be lower than that."
            )
        if labelled and (run.bag_count >= 100) != (changed["bag_count"] >= 100):
            raise DomainError(
                "Labels have been issued for this run. Its planned count cannot cross 100 now, "
                "because that changes how bag numbers are printed."
            )

    for key, value in changed.items():
        setattr(run, key, value)

    start, end = (_as_utc(getattr(run, name)) for name in times)
    unloaded = _as_utc(run.unloaded_at)
    if start and end and end < start:
        raise DomainError("The cycle cannot end before it starts.")
    if end and unloaded and unloaded < end:
        raise DomainError("The run cannot be unloaded before its cycle ends.")
    if start and unloaded and unloaded < start:
        raise DomainError("The run cannot be unloaded before its cycle starts.")

    db.commit()
    db.refresh(run)
    return run


def update_pasteurization_run(db: Session, pasteurization_run_id: int, data: dict):
    run = db.get(models.PasteurizationRun, pasteurization_run_id)
    if not run:
        return None
    if data.get("mix_lot_id") is not None and data["mix_lot_id"] != run.mix_lot_id:
        if db.get(models.MixLot, data["mix_lot_id"]) is None:
            raise NotFoundError("Mix lot not found")
    if (
        data.get("substrate_recipe_version_id") is not None
        and data["substrate_recipe_version_id"] != run.substrate_recipe_version_id
    ):
        _usable(db, models.SubstrateRecipeVersion, data["substrate_recipe_version_id"], "Substrate recipe")
    return _correct_run(
        db,
        run,
        models.Bag.pasteurization_run_id,
        data,
        label=f"Pasteurization run {run.run_code}",
        times=("steam_start_at", "steam_end_at"),
        fixed_once_bags_exist=("mix_lot_id", "substrate_recipe_version_id"),
        keep_when_null=("run_code", "mix_lot_id", "substrate_recipe_version_id", "unloaded_at", "bag_count"),
    )


# --- Sterilization runs ---

def create_sterilization_run(db: Session, data: dict):
    _usable(db, models.SpawnRecipe, data.get("spawn_recipe_id"), "Spawn recipe")
    _usable(db, models.GrainType, data.get("grain_type_id"), "Grain type")
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
    if sort_by not in STERILIZATION_RUN_SORT_FIELDS:
        raise DomainError(
            f"Cannot sort by '{sort_by}'. Use one of: {', '.join(STERILIZATION_RUN_SORT_FIELDS)}."
        )
    if sort_order not in ("asc", "desc"):
        raise DomainError("sort_order must be 'asc' or 'desc'.")
    sort_col = getattr(models.SterilizationRun, sort_by)
    stmt = stmt.order_by(
        sort_col.desc() if sort_order == "desc" else sort_col.asc(),
        models.SterilizationRun.sterilization_run_id.desc(),
    )
    return db.execute(stmt).scalars().all()


def get_sterilization_run(db: Session, sterilization_run_id: int):
    return db.get(models.SterilizationRun, sterilization_run_id)


def update_sterilization_run(db: Session, sterilization_run_id: int, data: dict):
    run = db.get(models.SterilizationRun, sterilization_run_id)
    if not run:
        return None
    if data.get("spawn_recipe_id") is not None and data["spawn_recipe_id"] != run.spawn_recipe_id:
        _usable(db, models.SpawnRecipe, data["spawn_recipe_id"], "Spawn recipe")
    if data.get("grain_type_id") is not None and data["grain_type_id"] != run.grain_type_id:
        _usable(db, models.GrainType, data["grain_type_id"], "Grain type")
    return _correct_run(
        db,
        run,
        models.Bag.sterilization_run_id,
        data,
        label=f"Sterilization run {run.run_code}",
        times=("cycle_start_at", "cycle_end_at"),
        fixed_once_bags_exist=("spawn_recipe_id", "grain_type_id"),
        keep_when_null=("run_code", "spawn_recipe_id", "grain_type_id", "unloaded_at", "bag_count"),
    )
