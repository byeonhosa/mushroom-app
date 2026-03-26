from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, model_validator


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


# --- Liquid cultures ---
class LiquidCultureCreate(BaseModel):
    culture_code: str
    species_id: int
    source: Optional[str] = None
    prepared_at: Optional[datetime] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = True


class LiquidCultureOut(BaseModel):
    liquid_culture_id: int
    culture_code: str
    species_id: int
    source: Optional[str] = None
    prepared_at: Optional[datetime] = None
    created_at: datetime
    notes: Optional[str] = None
    is_active: bool
    class Config: from_attributes = True


# --- Grain types ---
class GrainTypeCreate(BaseModel):
    name: str
    notes: Optional[str] = None


class GrainTypeUpdate(BaseModel):
    name: Optional[str] = None
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
    inoculation_source_type: Optional[Literal["LIQUID_CULTURE", "SPAWN_BAG"]] = None
    target_dry_kg: Optional[float] = None
    actual_dry_kg: Optional[float] = None
    dry_weight_kg: Optional[float] = None
    dry_weight_source: Optional[Literal["ACTUAL", "TARGET"]] = None
    bio_efficiency: Optional[float] = None
    created_at: datetime
    labeled_at: Optional[datetime] = None
    inoculated_at: Optional[datetime] = None
    incubation_start_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    fruiting_start_at: Optional[datetime] = None
    disposed_at: Optional[datetime] = None
    disposal_reason: Optional[Literal["CONTAMINATION", "FINAL_HARVEST"]] = None
    consumed_at: Optional[datetime] = None
    status: str
    notes: Optional[str] = None
    class Config: from_attributes = True


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
    occurred_at: datetime
    detail: Optional[str] = None
    notes: Optional[str] = None
    class Config: from_attributes = True


class BagDetailOut(BagOut):
    status_events: List["BagStatusEventOut"] = []
    harvest_events: List["HarvestEventOut"] = []
    child_bags: List["LineageChildBagOut"] = []
    child_summary: Optional["BagCollectionSummaryOut"] = None


# --- Inoculations ---
class InoculationCreate(BaseModel):
    substrate_bag_id: str
    spawn_bag_id: str
    inoculated_at: Optional[datetime] = None
    notes: Optional[str] = None


class SpawnInoculationBatchCreate(BaseModel):
    sterilization_run_id: int
    source_type: Literal["LIQUID_CULTURE", "SPAWN_BAG"]
    liquid_culture_id: Optional[int] = None
    donor_spawn_bag_id: Optional[str] = None
    bag_count: int = Field(..., gt=0)
    inoculated_at: Optional[datetime] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_source(self):
        if self.source_type == "LIQUID_CULTURE":
            if self.liquid_culture_id is None:
                raise ValueError("liquid_culture_id is required when source_type is LIQUID_CULTURE")
            if self.donor_spawn_bag_id is not None:
                raise ValueError("donor_spawn_bag_id must be omitted when source_type is LIQUID_CULTURE")
        if self.source_type == "SPAWN_BAG":
            if not self.donor_spawn_bag_id:
                raise ValueError("donor_spawn_bag_id is required when source_type is SPAWN_BAG")
            if self.liquid_culture_id is not None:
                raise ValueError("liquid_culture_id must be omitted when source_type is SPAWN_BAG")
        return self


class InoculationBatchCreate(BaseModel):
    spawn_bag_id: str
    pasteurization_run_id: int
    bag_count: int = Field(..., gt=0)
    inoculated_at: Optional[datetime] = None
    notes: Optional[str] = None


class InoculationOut(BaseModel):
    inoculation_id: int
    substrate_bag_id: str
    substrate_bag_ref: str
    spawn_bag_id: str
    spawn_bag_ref: str
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
    bag_ref: str
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


class ReadyUpdate(BaseModel):
    bag_id: str


class DisposalUpdate(BaseModel):
    bag_id: str
    disposal_reason: Literal["CONTAMINATION", "FINAL_HARVEST"]


class BagDryWeightUpdate(BaseModel):
    actual_dry_kg: Optional[float] = Field(default=None, gt=0)


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
    contaminated_at: Optional[datetime] = None
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
    inoculation_source_type: Optional[Literal["LIQUID_CULTURE", "SPAWN_BAG"]] = None
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
    generated_at: datetime
    summary: ProductionReportSummaryOut
    contamination_by_bag_type: List[ReportGroupOut]
    contamination_by_species: List[ReportGroupOut]
    contamination_by_liquid_culture: List[ReportGroupOut]
    contamination_by_inoculation_source_type: List[ReportGroupOut]
    contamination_by_spawn_generation: List[ReportGroupOut]
    contamination_by_source_sterilization_run: List[ReportGroupOut]
    contamination_by_pasteurization_run: List[ReportGroupOut]
    contamination_by_parent_spawn_bag: List[ReportGroupOut]
    contaminated_bags: List[ContaminationCaseOut]
    data_quality_issues: List[DataQualityIssueOut]
    pasteurization_runs: List[PasteurizationRunMetricsOut]
    substrate_bags: List[SubstrateBagMetricsOut]


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
