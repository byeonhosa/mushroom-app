import re
from datetime import date, datetime, timezone
from typing import Annotated, Optional, List, Literal
from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, model_validator


def _as_utc(value: datetime) -> datetime:
    """Normalise a time to UTC. SQLite hands back naive values, which are UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# SRS 5.2: every time the API sends carries its UTC offset, so that a browser
# never has to guess. Use UtcDatetime for every time in a response model.
UtcDatetime = Annotated[datetime, AfterValidator(_as_utc)]

# A time sent by a client must say which zone it is in. A value without an
# offset is refused; it would otherwise be stored as if it were UTC.
InputDatetime = Annotated[AwareDatetime, AfterValidator(_as_utc)]


def _clean_run_code(value: str) -> str:
    code = value.strip().upper()
    if not re.fullmatch(r"\d{6}[A-Z]", code):
        raise ValueError(
            "Run code must be the date as YYMMDD followed by a letter, for example 261109A."
        )
    return code


def _clean_species_code(value: str) -> str:
    code = value.strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{2,3}", code):
        raise ValueError("Species code must be two or three letters or digits, for example LM.")
    return code


# RUN-6: the run's date and a letter for its place in the day.
RunCode = Annotated[str, AfterValidator(_clean_run_code)]
# BAG-5: short enough to keep a bag code within 18 characters.
SpeciesCode = Annotated[str, AfterValidator(_clean_species_code)]


class HealthCheckOut(BaseModel):
    name: str
    ok: bool
    detail: Optional[str] = None


class HealthLiveOut(BaseModel):
    ok: bool
    service: str
    version: str
    environment: str
    checked_at: UtcDatetime


class HealthReadyOut(HealthLiveOut):
    database_backend: str
    pending_migrations: List[str]
    checks: List[HealthCheckOut]


# --- Sign-in and users (SRS 4.14) ---
class AuthStatusOut(BaseModel):
    setup_required: bool


class LoginIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=1, max_length=200)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=200)
    new_password: str = Field(..., min_length=1, max_length=200)


def _clean_email(value: str) -> str:
    email = value.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Enter an email address, for example name@example.com.")
    return email


EmailAddress = Annotated[str, AfterValidator(_clean_email)]
UserRoleName = Literal["admin", "operator"]


class CurrentUserOut(BaseModel):
    user_id: int
    email: str
    display_name: str
    role: UserRoleName
    must_change_password: bool
    model_config = ConfigDict(from_attributes=True)


class AccountUpdate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=120)


class UserOut(CurrentUserOut):
    is_active: bool
    created_at: UtcDatetime
    last_login_at: Optional[UtcDatetime] = None


class UserCreate(BaseModel):
    email: EmailAddress
    display_name: str = Field(..., min_length=1, max_length=120)
    role: UserRoleName = "operator"
    password: str = Field(..., min_length=1, max_length=200)


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    role: Optional[UserRoleName] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=1, max_length=200)


def _clean_name(value: str) -> str:
    """A name or code as a person typed it: outer spaces removed, and not empty."""
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError("This cannot be empty.")
    return cleaned


def _clean_recipe_code(value: str) -> str:
    cleaned = _clean_name(value).upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9-]*", cleaned):
        raise ValueError("A recipe code is capital letters, digits and hyphens, for example MM or GRAIN-1.")
    return cleaned


Name = Annotated[str, AfterValidator(_clean_name)]
RecipeCode = Annotated[str, AfterValidator(_clean_recipe_code)]


# --- Fill profiles ---
class FillProfileCreate(BaseModel):
    name: Name = Field(..., max_length=120)
    target_dry_kg_per_bag: float = Field(..., gt=0, le=50)
    target_water_kg_per_bag: float = Field(..., ge=0, le=50)
    notes: Optional[str] = None


class FillProfileUpdate(BaseModel):
    name: Optional[Name] = Field(default=None, max_length=120)
    target_dry_kg_per_bag: Optional[float] = Field(default=None, gt=0, le=50)
    target_water_kg_per_bag: Optional[float] = Field(default=None, ge=0, le=50)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class FillProfileOut(BaseModel):
    fill_profile_id: int
    name: str
    target_dry_kg_per_bag: float
    target_water_kg_per_bag: float
    notes: Optional[str] = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


# --- Substrate recipe versions ---
class SubstrateRecipeVersionCreate(BaseModel):
    name: Name = Field(..., max_length=120)
    recipe_code: RecipeCode = Field(..., max_length=20)
    notes: Optional[str] = None


class SubstrateRecipeVersionUpdate(BaseModel):
    name: Optional[Name] = Field(default=None, max_length=120)
    recipe_code: Optional[RecipeCode] = Field(default=None, max_length=20)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class SubstrateRecipeVersionOut(BaseModel):
    substrate_recipe_version_id: int
    name: str
    recipe_code: str
    notes: Optional[str] = None
    is_active: bool
    created_at: UtcDatetime
    model_config = ConfigDict(from_attributes=True)


# --- Spawn recipes ---
class SpawnRecipeCreate(BaseModel):
    recipe_code: RecipeCode = Field(..., max_length=40)
    notes: Optional[str] = None


class SpawnRecipeUpdate(BaseModel):
    recipe_code: Optional[RecipeCode] = Field(default=None, max_length=40)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class SpawnRecipeOut(BaseModel):
    spawn_recipe_id: int
    recipe_code: str
    notes: Optional[str] = None
    is_active: bool
    created_at: UtcDatetime
    model_config = ConfigDict(from_attributes=True)


# --- Mix lots ---
class MixLotCreate(BaseModel):
    lot_code: Name = Field(..., max_length=120)
    substrate_recipe_version_id: int
    fill_profile_id: int
    mixed_at: Optional[InputDatetime] = None
    notes: Optional[str] = None


class MixLotUpdate(BaseModel):
    """A correction to a mix lot (REF-8). Only the fields sent are changed."""

    lot_code: Optional[Name] = Field(default=None, max_length=120)
    substrate_recipe_version_id: Optional[int] = None
    fill_profile_id: Optional[int] = None
    mixed_at: Optional[InputDatetime] = None
    notes: Optional[str] = None


class MixLotOut(BaseModel):
    mix_lot_id: int
    lot_code: str
    substrate_recipe_version_id: int
    fill_profile_id: int
    mixed_at: UtcDatetime
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# --- Species ---
# The farm website's vocabulary (models.AVAILABILITY_TIERS, models.SALE_PATHS).
AvailabilityTier = Literal["year-round", "in-rotation-now", "returning", "wholesale-only", "functional-coming-later"]
SalePath = Literal[
    "available", "low-stock", "sold-out", "coming-soon", "seasonal",
    "preorder", "hidden", "wholesale-only", "inquiry-only",
]


def slugify(text: str) -> str:
    """The website's rule: lower case, anything else becomes a hyphen. Lion's Mane -> lion-s-mane."""
    return re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")


def _clean_slug(value: str) -> str:
    slug = value.strip().lower()
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug) or len(slug) > 60:
        raise ValueError("A slug is lower-case letters and digits joined by hyphens, for example blue-oyster.")
    return slug


Slug = Annotated[str, AfterValidator(_clean_slug)]


class MushroomSpeciesCreate(BaseModel):
    code: SpeciesCode
    name: str = Field(..., min_length=1, max_length=120)
    latin_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = True
    # Left out, the slug is made from the name. It never changes afterwards.
    slug: Optional[Slug] = None
    availability_tier: Optional[AvailabilityTier] = None
    sale_path: SalePath = "hidden"
    in_rotation_now: bool = False
    restrictions: Optional[str] = None


class MushroomSpeciesUpdate(BaseModel):
    code: Optional[SpeciesCode] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    latin_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    slug: Optional[Slug] = None
    availability_tier: Optional[AvailabilityTier] = None
    sale_path: Optional[SalePath] = None
    in_rotation_now: Optional[bool] = None
    restrictions: Optional[str] = None


class MushroomSpeciesOut(BaseModel):
    species_id: int
    code: str
    name: str
    latin_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    slug: Optional[str] = None
    availability_tier: Optional[AvailabilityTier] = None
    sale_path: SalePath
    in_rotation_now: bool
    restrictions: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# --- Species profiles (read-only cultivation reference) ---
# Mirrors models.SpeciesProfile. Range fields are nullable ints (*_low / *_high);
# `use_type` and `pinning_trigger` are effectively enums (allowed values live in
# the seed JSON _meta.conventions and the model docstring).
class SpeciesProfileOut(BaseModel):
    species_profile_id: int
    species_id: int
    # The label code of the species (LM); `code` below is its slug (lion-s-mane).
    species_code: Optional[str] = None
    # SPR-2: whether the values come from the farm's sources or outside research.
    data_source: Literal["farm", "researched"]
    source_note: Optional[str] = None
    code: str
    common_name: str
    scientific_name: Optional[str] = None
    difficulty: Optional[str] = None
    difficulty_rank: Optional[int] = None
    use_type: Optional[str] = None
    substrate_primary: Optional[str] = None
    substrate_moisture_pct_low: Optional[int] = None
    substrate_moisture_pct_high: Optional[int] = None
    spawn_rate_pct_low: Optional[int] = None
    spawn_rate_pct_high: Optional[int] = None
    incubation_temp_f_low: Optional[int] = None
    incubation_temp_f_high: Optional[int] = None
    colonization_days_low: Optional[int] = None
    colonization_days_high: Optional[int] = None
    fruiting_temp_f_low: Optional[int] = None
    fruiting_temp_f_high: Optional[int] = None
    fruiting_humidity_pct_low: Optional[int] = None
    fruiting_humidity_pct_high: Optional[int] = None
    fruiting_co2_ppm_low: Optional[int] = None
    fruiting_co2_ppm_high: Optional[int] = None
    fae_ach_low: Optional[int] = None
    fae_ach_high: Optional[int] = None
    light_lux_low: Optional[int] = None
    light_lux_high: Optional[int] = None
    light_hours_per_day_low: Optional[int] = None
    light_hours_per_day_high: Optional[int] = None
    pinning_trigger: Optional[str] = None
    pin_to_harvest_days_low: Optional[int] = None
    pin_to_harvest_days_high: Optional[int] = None
    biological_efficiency_pct_low: Optional[int] = None
    biological_efficiency_pct_high: Optional[int] = None
    typical_flushes_low: Optional[int] = None
    typical_flushes_high: Optional[int] = None
    yield_notes: Optional[str] = None
    pricing_notes: Optional[str] = None
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# --- Liquid cultures ---
class LiquidCultureCreate(BaseModel):
    culture_code: Name = Field(..., max_length=120)
    species_id: int
    source: Optional[str] = None
    prepared_at: Optional[InputDatetime] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = True
    parent_liquid_culture_id: Optional[int] = None


class LiquidCultureUpdate(BaseModel):
    """The code and the species are fixed once the culture exists: bag codes and lineage rest on them."""

    source: Optional[str] = None
    prepared_at: Optional[InputDatetime] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    parent_liquid_culture_id: Optional[int] = None


class LiquidCultureOut(BaseModel):
    liquid_culture_id: int
    culture_code: str
    species_id: int
    source: Optional[str] = None
    prepared_at: Optional[UtcDatetime] = None
    created_at: UtcDatetime
    notes: Optional[str] = None
    is_active: bool
    parent_liquid_culture_id: Optional[int] = None
    parent_culture_code: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# --- Purchased spawn lots (REF-11) ---
class PurchasedSpawnLotCreate(BaseModel):
    vendor: str = Field(..., min_length=1, max_length=160)
    vendor_lot_number: Optional[str] = Field(default=None, max_length=120)
    species_id: int
    grain_type_id: Optional[int] = None
    received_at: InputDatetime
    quantity: Optional[float] = Field(default=None, gt=0)
    quantity_unit: Optional[str] = Field(default=None, max_length=20)
    notes: Optional[str] = None


class PurchasedSpawnLotUpdate(BaseModel):
    vendor: Optional[str] = Field(default=None, min_length=1, max_length=160)
    vendor_lot_number: Optional[str] = Field(default=None, max_length=120)
    species_id: Optional[int] = None
    grain_type_id: Optional[int] = None
    received_at: Optional[InputDatetime] = None
    quantity: Optional[float] = Field(default=None, gt=0)
    quantity_unit: Optional[str] = Field(default=None, max_length=20)
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    # INO-7: true marks the lot used up; false reopens it.
    used_up: Optional[bool] = None


class PurchasedSpawnLotOut(BaseModel):
    purchased_spawn_lot_id: int
    lot_code: str
    vendor: str
    vendor_lot_number: Optional[str] = None
    species_id: int
    species_code: Optional[str] = None
    species_name: Optional[str] = None
    grain_type_id: Optional[int] = None
    grain_type_name: Optional[str] = None
    received_at: UtcDatetime
    quantity: Optional[float] = None
    quantity_unit: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    is_used_up: bool
    used_up_at: Optional[UtcDatetime] = None
    created_at: UtcDatetime
    model_config = ConfigDict(from_attributes=True)


# --- Grain types ---
class GrainTypeCreate(BaseModel):
    name: Name = Field(..., max_length=80)
    notes: Optional[str] = None


class GrainTypeUpdate(BaseModel):
    name: Optional[Name] = Field(default=None, max_length=80)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class GrainTypeOut(BaseModel):
    grain_type_id: int
    name: str
    notes: Optional[str] = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


# --- Pasteurization runs ---
class PasteurizationRunCreate(BaseModel):
    run_code: RunCode
    mix_lot_id: int
    substrate_recipe_version_id: int
    steam_start_at: Optional[InputDatetime] = None
    steam_end_at: Optional[InputDatetime] = None
    unloaded_at: InputDatetime
    bag_count: int = Field(..., gt=0, le=999)
    notes: Optional[str] = None


class PasteurizationRunUpdate(BaseModel):
    """A correction to a run (RUN-5). Only the fields sent are changed."""

    run_code: Optional[RunCode] = None
    mix_lot_id: Optional[int] = None
    substrate_recipe_version_id: Optional[int] = None
    steam_start_at: Optional[InputDatetime] = None
    steam_end_at: Optional[InputDatetime] = None
    unloaded_at: Optional[InputDatetime] = None
    bag_count: Optional[int] = Field(default=None, gt=0, le=999)
    notes: Optional[str] = None


class PasteurizationRunOut(BaseModel):
    pasteurization_run_id: int
    run_code: str
    mix_lot_id: int
    substrate_recipe_version_id: int
    steam_start_at: Optional[UtcDatetime] = None
    steam_end_at: Optional[UtcDatetime] = None
    unloaded_at: UtcDatetime
    bag_count: int
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class NextRunCodeOut(BaseModel):
    run_code: str
    run_date: date


# --- Sterilization runs ---
class SterilizationRunCreate(BaseModel):
    run_code: RunCode
    spawn_recipe_id: int
    grain_type_id: int
    cycle_start_at: Optional[InputDatetime] = None
    cycle_end_at: Optional[InputDatetime] = None
    unloaded_at: InputDatetime
    bag_count: int = Field(..., gt=0, le=999)
    temp_c: Optional[float] = None
    psi: Optional[float] = None
    hold_minutes: Optional[int] = None
    notes: Optional[str] = None


class SterilizationRunUpdate(BaseModel):
    """A correction to a run (RUN-5). Only the fields sent are changed."""

    run_code: Optional[RunCode] = None
    spawn_recipe_id: Optional[int] = None
    grain_type_id: Optional[int] = None
    cycle_start_at: Optional[InputDatetime] = None
    cycle_end_at: Optional[InputDatetime] = None
    unloaded_at: Optional[InputDatetime] = None
    bag_count: Optional[int] = Field(default=None, gt=0, le=999)
    temp_c: Optional[float] = None
    psi: Optional[float] = None
    hold_minutes: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None


class SterilizationRunOut(BaseModel):
    sterilization_run_id: int
    run_code: str
    spawn_recipe_id: int
    grain_type_id: int
    cycle_start_at: Optional[UtcDatetime] = None
    cycle_end_at: Optional[UtcDatetime] = None
    unloaded_at: UtcDatetime
    bag_count: int
    temp_c: Optional[float] = None
    psi: Optional[float] = None
    hold_minutes: Optional[int] = None
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# --- Bags ---
class BagCreateSpawn(BaseModel):
    """Create unlabeled spawn bag records from a sterilization run."""
    sterilization_run_id: int
    bag_count: int = Field(default=1, gt=0)


class BagCreateSubstrate(BaseModel):
    """Create unlabeled substrate bag records from a pasteurization run."""
    pasteurization_run_id: int
    bag_count: int = Field(default=1, gt=0)
    actual_dry_kg: Optional[float] = Field(default=None, gt=0)


class BagOut(BaseModel):
    bag_id: str
    bag_code: Optional[str] = None
    bag_ref: str
    bag_type: Literal["SPAWN", "SUBSTRATE"]
    species_id: Optional[int] = None
    pasteurization_run_id: Optional[int] = None
    sterilization_run_id: Optional[int] = None
    mix_lot_id: Optional[int] = None
    substrate_recipe_version_id: Optional[int] = None
    spawn_recipe_id: Optional[int] = None
    grain_type_id: Optional[int] = None
    parent_spawn_bag_id: Optional[str] = None
    parent_spawn_bag_ref: Optional[str] = None
    source_spawn_bag_id: Optional[str] = None
    source_spawn_bag_ref: Optional[str] = None
    source_liquid_culture_id: Optional[int] = None
    source_liquid_culture_code: Optional[str] = None
    source_purchased_spawn_lot_id: Optional[int] = None
    source_purchased_spawn_lot_code: Optional[str] = None
    inoculation_source_type: Optional[Literal["LIQUID_CULTURE", "SPAWN_BAG", "PURCHASED_SPAWN"]] = None
    target_dry_kg: Optional[float] = None
    actual_dry_kg: Optional[float] = None
    dry_weight_kg: Optional[float] = None
    dry_weight_source: Optional[Literal["ACTUAL", "TARGET"]] = None
    bio_efficiency: Optional[float] = None
    created_at: UtcDatetime
    labeled_at: Optional[UtcDatetime] = None
    inoculated_at: Optional[UtcDatetime] = None
    incubation_start_at: Optional[UtcDatetime] = None
    ready_at: Optional[UtcDatetime] = None
    fruiting_start_at: Optional[UtcDatetime] = None
    disposed_at: Optional[UtcDatetime] = None
    disposal_reason: Optional[Literal["CONTAMINATION", "FINAL_HARVEST"]] = None
    consumed_at: Optional[UtcDatetime] = None
    status: str
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class BagStatusEventOut(BaseModel):
    bag_status_event_id: int
    bag_id: str
    event_type: Literal[
        "CREATED",
        "STERILIZED",
        "PASTEURIZED",
        "BAG_CODE_ASSIGNED",
        "INOCULATED",
        "INCUBATION_STARTED",
        "READY",
        "FRUITING_STARTED",
        "HARVEST_RECORDED",
        "CONSUMED",
        "DISPOSED",
    ]
    occurred_at: UtcDatetime
    detail: Optional[str] = None
    notes: Optional[str] = None
    # USR-4: the name of the user who entered the event, when known.
    recorded_by_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class BagDetailOut(BagOut):
    status_events: List["BagStatusEventOut"] = []
    harvest_events: List["HarvestEventOut"] = []
    child_bags: List["LineageChildBagOut"] = []
    child_summary: Optional["BagCollectionSummaryOut"] = None


# --- Inoculations ---
class InoculationCreate(BaseModel):
    substrate_bag_id: str
    spawn_bag_id: str
    inoculated_at: Optional[InputDatetime] = None
    notes: Optional[str] = None


class SpawnInoculationBatchCreate(BaseModel):
    """Inoculate unlabeled spawn bags of a run from one source (INO-1, INO-2, INO-6)."""

    sterilization_run_id: int
    source_type: Literal["LIQUID_CULTURE", "SPAWN_BAG", "PURCHASED_SPAWN"]
    liquid_culture_id: Optional[int] = None
    donor_spawn_bag_id: Optional[str] = None
    purchased_spawn_lot_id: Optional[int] = None
    bag_count: int = Field(..., gt=0)
    inoculated_at: Optional[InputDatetime] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_source(self):
        given = {
            "LIQUID_CULTURE": self.liquid_culture_id is not None,
            "SPAWN_BAG": bool(self.donor_spawn_bag_id),
            "PURCHASED_SPAWN": self.purchased_spawn_lot_id is not None,
        }
        field = {
            "LIQUID_CULTURE": "liquid_culture_id",
            "SPAWN_BAG": "donor_spawn_bag_id",
            "PURCHASED_SPAWN": "purchased_spawn_lot_id",
        }
        if not given[self.source_type]:
            raise ValueError(f"{field[self.source_type]} is required when source_type is {self.source_type}")
        for other, present in given.items():
            if other != self.source_type and present:
                raise ValueError(f"{field[other]} must be omitted when source_type is {self.source_type}")
        return self


class InoculationBatchCreate(BaseModel):
    """Inoculate unlabeled substrate bags of a run from a ready spawn bag or a purchased spawn lot (INO-3, INO-6)."""

    spawn_bag_id: Optional[str] = None
    purchased_spawn_lot_id: Optional[int] = None
    pasteurization_run_id: int
    bag_count: int = Field(..., gt=0)
    inoculated_at: Optional[InputDatetime] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_source(self):
        if bool(self.spawn_bag_id) == (self.purchased_spawn_lot_id is not None):
            raise ValueError("Give exactly one source: spawn_bag_id or purchased_spawn_lot_id")
        return self


class InoculationOut(BaseModel):
    inoculation_id: int
    substrate_bag_id: str
    substrate_bag_ref: str
    spawn_bag_id: str
    spawn_bag_ref: str
    inoculated_at: UtcDatetime
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# --- Harvest events ---
class HarvestEventCreate(BaseModel):
    bag_id: str
    flush_number: Literal[1, 2]
    fresh_weight_kg: float = Field(..., gt=0)
    harvested_at: Optional[InputDatetime] = None
    notes: Optional[str] = None


class HarvestEventOut(BaseModel):
    harvest_event_id: int
    bag_id: str
    bag_ref: str
    flush_number: Literal[1, 2]
    fresh_weight_kg: float
    harvested_at: UtcDatetime
    notes: Optional[str] = None
    recorded_by_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# --- Event recording (scan flow) ---
class IncubationStartUpdate(BaseModel):
    bag_id: str


class FruitingStartUpdate(BaseModel):
    bag_id: str


class ReadyUpdate(BaseModel):
    bag_id: str


class DisposalUpdate(BaseModel):
    bag_id: str
    disposal_reason: Literal["CONTAMINATION", "FINAL_HARVEST"]


class BagDryWeightUpdate(BaseModel):
    actual_dry_kg: Optional[float] = Field(default=None, gt=0)


# --- Ingredients (reference) ---
class IngredientCreate(BaseModel):
    name: Name = Field(..., max_length=120)
    category: Optional[str] = None
    notes: Optional[str] = None


class IngredientUpdate(BaseModel):
    name: Optional[Name] = Field(default=None, max_length=120)
    category: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class IngredientOut(BaseModel):
    ingredient_id: int
    name: str
    category: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class IngredientLotCreate(BaseModel):
    ingredient_id: int
    vendor: Optional[str] = None
    lot_code: Optional[str] = None
    received_at: Optional[InputDatetime] = None
    unit_cost_per_kg: Optional[float] = None
    notes: Optional[str] = None


class IngredientLotOut(BaseModel):
    ingredient_lot_id: int
    ingredient_id: int
    vendor: Optional[str] = None
    lot_code: Optional[str] = None
    received_at: Optional[UtcDatetime] = None
    unit_cost_per_kg: Optional[float] = None
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# --- Labels ---
class LabelRequest(BaseModel):
    bag_ids: List[str]


# --- Reporting ---
class ReportGroupOut(BaseModel):
    key: str
    label: str
    total_bags: int
    contaminated_bags: int
    contamination_rate: float


class PasteurizationRunMetricsOut(BaseModel):
    pasteurization_run_id: int
    run_code: str
    total_bags: int
    contaminated_bags: int
    contamination_rate: float
    total_harvest_kg: float
    total_dry_weight_kg: float
    bio_efficiency: Optional[float] = None


class SubstrateBagMetricsOut(BaseModel):
    bag_id: str
    bag_code: Optional[str] = None
    bag_ref: str
    status: str
    disposal_reason: Optional[Literal["CONTAMINATION", "FINAL_HARVEST"]] = None
    species_id: Optional[int] = None
    species_code: Optional[str] = None
    species_name: Optional[str] = None
    pasteurization_run_id: Optional[int] = None
    pasteurization_run_code: Optional[str] = None
    parent_spawn_bag_id: Optional[str] = None
    parent_spawn_bag_ref: Optional[str] = None
    source_liquid_culture_id: Optional[int] = None
    source_liquid_culture_code: Optional[str] = None
    source_purchased_spawn_lot_id: Optional[int] = None
    source_purchased_spawn_lot_code: Optional[str] = None
    spawn_generation: Optional[int] = None
    source_sterilization_run_id: Optional[int] = None
    source_sterilization_run_code: Optional[str] = None
    target_dry_kg: Optional[float] = None
    actual_dry_kg: Optional[float] = None
    dry_weight_kg: Optional[float] = None
    dry_weight_source: Optional[Literal["ACTUAL", "TARGET"]] = None
    total_harvest_kg: float
    bio_efficiency: Optional[float] = None
    contaminated: bool


class ContaminationCaseOut(BaseModel):
    bag_id: str
    bag_code: Optional[str] = None
    bag_ref: str
    bag_type: Literal["SPAWN", "SUBSTRATE"]
    status: str
    disposal_reason: Optional[Literal["CONTAMINATION", "FINAL_HARVEST"]] = None
    contaminated_at: Optional[UtcDatetime] = None
    species_id: Optional[int] = None
    species_code: Optional[str] = None
    species_name: Optional[str] = None
    sterilization_run_id: Optional[int] = None
    sterilization_run_code: Optional[str] = None
    pasteurization_run_id: Optional[int] = None
    pasteurization_run_code: Optional[str] = None
    parent_spawn_bag_id: Optional[str] = None
    parent_spawn_bag_ref: Optional[str] = None
    source_liquid_culture_id: Optional[int] = None
    source_liquid_culture_code: Optional[str] = None
    spawn_generation: Optional[int] = None
    source_sterilization_run_id: Optional[int] = None
    source_sterilization_run_code: Optional[str] = None


class DataQualityIssueOut(BaseModel):
    code: str
    label: str
    count: int
    bag_refs: List[str]


class LineageChildBagOut(BaseModel):
    generation: int
    bag_id: str
    bag_code: Optional[str] = None
    bag_ref: str
    bag_type: Literal["SPAWN", "SUBSTRATE"]
    status: str
    disposal_reason: Optional[Literal["CONTAMINATION", "FINAL_HARVEST"]] = None
    species_id: Optional[int] = None
    species_code: Optional[str] = None
    species_name: Optional[str] = None
    sterilization_run_id: Optional[int] = None
    sterilization_run_code: Optional[str] = None
    pasteurization_run_id: Optional[int] = None
    pasteurization_run_code: Optional[str] = None
    parent_spawn_bag_id: Optional[str] = None
    parent_spawn_bag_ref: Optional[str] = None
    source_liquid_culture_id: Optional[int] = None
    source_liquid_culture_code: Optional[str] = None
    source_purchased_spawn_lot_id: Optional[int] = None
    source_purchased_spawn_lot_code: Optional[str] = None
    inoculation_source_type: Optional[Literal["LIQUID_CULTURE", "SPAWN_BAG", "PURCHASED_SPAWN"]] = None
    source_sterilization_run_id: Optional[int] = None
    source_sterilization_run_code: Optional[str] = None
    target_dry_kg: Optional[float] = None
    actual_dry_kg: Optional[float] = None
    dry_weight_kg: Optional[float] = None
    dry_weight_source: Optional[Literal["ACTUAL", "TARGET"]] = None
    total_harvest_kg: float
    bio_efficiency: Optional[float] = None
    contaminated: bool


class ProductionReportSummaryOut(BaseModel):
    total_spawn_bags: int
    total_substrate_bags: int
    total_contaminated_bags: int
    contamination_rate: float
    substrate_bags_with_harvest: int
    substrate_bags_with_dry_weight: int
    total_harvest_kg: float
    total_dry_weight_kg: float
    overall_bio_efficiency: Optional[float] = None


class ProductionReportOut(BaseModel):
    generated_at: UtcDatetime
    summary: ProductionReportSummaryOut
    contamination_by_bag_type: List[ReportGroupOut]
    contamination_by_species: List[ReportGroupOut]
    contamination_by_liquid_culture: List[ReportGroupOut]
    contamination_by_inoculation_source_type: List[ReportGroupOut]
    contamination_by_purchased_spawn_lot: List[ReportGroupOut]
    contamination_by_spawn_generation: List[ReportGroupOut]
    contamination_by_source_sterilization_run: List[ReportGroupOut]
    contamination_by_pasteurization_run: List[ReportGroupOut]
    contamination_by_parent_spawn_bag: List[ReportGroupOut]
    contaminated_bags: List[ContaminationCaseOut]
    data_quality_issues: List[DataQualityIssueOut]
    pasteurization_runs: List[PasteurizationRunMetricsOut]
    substrate_bags: List[SubstrateBagMetricsOut]


class DashboardQueueOut(BaseModel):
    key: str
    label: str
    count: int
    description: str
    href: str
    tone: Literal["default", "action", "warning"]


class DashboardRunSummaryOut(BaseModel):
    run_type: Literal["STERILIZATION", "PASTEURIZATION"]
    run_id: int
    run_code: str
    unloaded_at: UtcDatetime
    planned_bag_count: int
    total_bags: int
    unlabeled_bags: int
    ready_bags: int
    fruiting_bags: int
    contaminated_bags: int
    harvested_bags: int
    downstream_bags: int
    next_action: str
    href: str


class DashboardActivityOut(BaseModel):
    occurred_at: UtcDatetime
    bag_id: str
    bag_ref: str
    bag_type: Literal["SPAWN", "SUBSTRATE"]
    event_type: str
    title: str
    detail: Optional[str] = None
    href: str


class DashboardAlertOut(BaseModel):
    severity: Literal["info", "warning"]
    title: str
    detail: str
    href: str


class DashboardOverviewOut(BaseModel):
    generated_at: UtcDatetime
    summary: ProductionReportSummaryOut
    queues: List[DashboardQueueOut]
    sterilization_runs: List[DashboardRunSummaryOut]
    pasteurization_runs: List[DashboardRunSummaryOut]
    recent_activity: List[DashboardActivityOut]
    alerts: List[DashboardAlertOut]


class BagCollectionSummaryOut(BaseModel):
    total_bags: int
    unlabeled_bags: int
    inoculated_bags: int
    ready_bags: int
    fruiting_bags: int
    contaminated_bags: int
    harvested_bags: int
    consumed_bags: int
    total_harvest_kg: float
    total_dry_weight_kg: float
    overall_bio_efficiency: Optional[float] = None


class SterilizationRunDetailOut(SterilizationRunOut):
    bags: List[BagOut]
    summary: BagCollectionSummaryOut
    downstream_substrate_bags: List[SubstrateBagMetricsOut]
    downstream_summary: BagCollectionSummaryOut


class PasteurizationRunDetailOut(PasteurizationRunOut):
    bags: List[SubstrateBagMetricsOut]
    summary: BagCollectionSummaryOut


# Forward ref for BagDetailOut
BagDetailOut.model_rebuild()
