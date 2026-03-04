from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# --- Fill profiles ---
class FillProfileCreate(BaseModel):
    name: str
    target_dry_kg_per_bag: float
    target_water_kg_per_bag: float
    notes: Optional[str] = None


class FillProfileOut(FillProfileCreate):
    fill_profile_id: int
    class Config: from_attributes = True


# --- Substrate recipe versions ---
class SubstrateRecipeVersionCreate(BaseModel):
    name: str
    recipe_code: str
    notes: Optional[str] = None


class SubstrateRecipeVersionOut(SubstrateRecipeVersionCreate):
    substrate_recipe_version_id: int
    created_at: datetime
    class Config: from_attributes = True


# --- Spawn recipes ---
class SpawnRecipeCreate(BaseModel):
    recipe_code: str
    notes: Optional[str] = None


class SpawnRecipeOut(SpawnRecipeCreate):
    spawn_recipe_id: int
    created_at: datetime
    class Config: from_attributes = True


# --- Mix lots ---
class MixLotCreate(BaseModel):
    lot_code: str
    substrate_recipe_version_id: int
    fill_profile_id: int
    mixed_at: Optional[datetime] = None
    notes: Optional[str] = None


class MixLotOut(BaseModel):
    mix_lot_id: int
    lot_code: str
    substrate_recipe_version_id: int
    fill_profile_id: int
    mixed_at: datetime
    notes: Optional[str] = None
    class Config: from_attributes = True


# --- Species ---
class MushroomSpeciesCreate(BaseModel):
    code: str
    name: str
    latin_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = True


class MushroomSpeciesUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    latin_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class MushroomSpeciesOut(BaseModel):
    species_id: int
    code: str
    name: str
    latin_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    class Config: from_attributes = True


# --- Grain types ---
class GrainTypeCreate(BaseModel):
    name: str
    notes: Optional[str] = None


class GrainTypeOut(BaseModel):
    grain_type_id: int
    name: str
    notes: Optional[str] = None
    class Config: from_attributes = True


# --- Pasteurization runs ---
class PasteurizationRunCreate(BaseModel):
    run_code: str
    mix_lot_id: int
    substrate_recipe_version_id: int
    steam_start_at: Optional[datetime] = None
    steam_end_at: Optional[datetime] = None
    unloaded_at: datetime
    bag_count: int
    notes: Optional[str] = None


class PasteurizationRunOut(BaseModel):
    pasteurization_run_id: int
    run_code: str
    mix_lot_id: int
    substrate_recipe_version_id: int
    steam_start_at: Optional[datetime] = None
    steam_end_at: Optional[datetime] = None
    unloaded_at: datetime
    bag_count: int
    notes: Optional[str] = None
    class Config: from_attributes = True


# --- Sterilization runs ---
class SterilizationRunCreate(BaseModel):
    run_code: str
    spawn_recipe_id: int
    grain_type_id: int
    cycle_start_at: Optional[datetime] = None
    cycle_end_at: Optional[datetime] = None
    unloaded_at: datetime
    bag_count: int
    temp_c: Optional[float] = None
    psi: Optional[float] = None
    hold_minutes: Optional[int] = None
    notes: Optional[str] = None


class SterilizationRunOut(BaseModel):
    sterilization_run_id: int
    run_code: str
    spawn_recipe_id: int
    grain_type_id: int
    cycle_start_at: Optional[datetime] = None
    cycle_end_at: Optional[datetime] = None
    unloaded_at: datetime
    bag_count: int
    temp_c: Optional[float] = None
    psi: Optional[float] = None
    hold_minutes: Optional[int] = None
    notes: Optional[str] = None
    class Config: from_attributes = True


# --- Bags ---
class BagCreateSpawn(BaseModel):
    """Create spawn bags from a sterilization run."""
    sterilization_run_id: int
    species_id: int
    bag_count: int = 1


class BagCreateSubstrate(BaseModel):
    """Create substrate bags from a pasteurization run."""
    pasteurization_run_id: int
    species_id: int
    bag_count: int = 1


class BagOut(BaseModel):
    bag_id: str
    bag_type: Literal["SPAWN", "SUBSTRATE"]
    species_id: int
    pasteurization_run_id: Optional[int] = None
    sterilization_run_id: Optional[int] = None
    mix_lot_id: Optional[int] = None
    substrate_recipe_version_id: Optional[int] = None
    spawn_recipe_id: Optional[int] = None
    grain_type_id: Optional[int] = None
    parent_spawn_bag_id: Optional[str] = None
    created_at: datetime
    inoculated_at: Optional[datetime] = None
    incubation_start_at: Optional[datetime] = None
    fruiting_start_at: Optional[datetime] = None
    disposed_at: Optional[datetime] = None
    disposal_reason: Optional[Literal["CONTAMINATION", "FINAL_HARVEST"]] = None
    consumed_at: Optional[datetime] = None
    status: str
    notes: Optional[str] = None
    class Config: from_attributes = True


class BagDetailOut(BagOut):
    harvest_events: List["HarvestEventOut"] = []


# --- Inoculations ---
class InoculationCreate(BaseModel):
    substrate_bag_id: str
    spawn_bag_id: str
    inoculated_at: Optional[datetime] = None
    notes: Optional[str] = None


class InoculationOut(BaseModel):
    inoculation_id: int
    substrate_bag_id: str
    spawn_bag_id: str
    inoculated_at: datetime
    notes: Optional[str] = None
    class Config: from_attributes = True


# --- Harvest events ---
class HarvestEventCreate(BaseModel):
    bag_id: str
    flush_number: Literal[1, 2]
    fresh_weight_kg: float = Field(..., gt=0)
    harvested_at: Optional[datetime] = None
    notes: Optional[str] = None


class HarvestEventOut(BaseModel):
    harvest_event_id: int
    bag_id: str
    flush_number: Literal[1, 2]
    fresh_weight_kg: float
    harvested_at: datetime
    notes: Optional[str] = None
    class Config: from_attributes = True


# --- Event recording (scan flow) ---
class IncubationStartUpdate(BaseModel):
    bag_id: str


class FruitingStartUpdate(BaseModel):
    bag_id: str


class DisposalUpdate(BaseModel):
    bag_id: str
    disposal_reason: Literal["CONTAMINATION", "FINAL_HARVEST"]


# --- Ingredients (reference) ---
class IngredientCreate(BaseModel):
    name: str
    category: Optional[str] = None
    notes: Optional[str] = None


class IngredientOut(BaseModel):
    ingredient_id: int
    name: str
    category: Optional[str] = None
    notes: Optional[str] = None
    class Config: from_attributes = True


class IngredientLotCreate(BaseModel):
    ingredient_id: int
    vendor: Optional[str] = None
    lot_code: Optional[str] = None
    received_at: Optional[datetime] = None
    unit_cost_per_kg: Optional[float] = None
    notes: Optional[str] = None


class IngredientLotOut(BaseModel):
    ingredient_lot_id: int
    ingredient_id: int
    vendor: Optional[str] = None
    lot_code: Optional[str] = None
    received_at: Optional[datetime] = None
    unit_cost_per_kg: Optional[float] = None
    notes: Optional[str] = None
    class Config: from_attributes = True


# --- Labels ---
class LabelRequest(BaseModel):
    bag_ids: List[str]


# Forward ref for BagDetailOut
BagDetailOut.model_rebuild()
