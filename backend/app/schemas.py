from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

class FillProfileCreate(BaseModel):
    name: str
    target_dry_kg_per_bag: float
    target_water_kg_per_bag: float
    notes: Optional[str] = None

class FillProfileOut(FillProfileCreate):
    fill_profile_id: int
    class Config: from_attributes = True

class SpawnBatchCreate(BaseModel):
    spawn_type: Literal["PURCHASED_BLOCK", "IN_HOUSE_GRAIN"]
    strain_code: str
    vendor: Optional[str] = None
    lot_code: Optional[str] = None
    made_at: Optional[datetime] = None
    incubation_start_at: Optional[datetime] = None
    notes: Optional[str] = None

class SpawnBatchUpdate(BaseModel):
    spawn_type: Optional[Literal["PURCHASED_BLOCK", "IN_HOUSE_GRAIN"]] = None
    strain_code: Optional[str] = None
    vendor: Optional[str] = None
    lot_code: Optional[str] = None
    made_at: Optional[datetime] = None
    incubation_start_at: Optional[datetime] = None
    notes: Optional[str] = None

class SpawnBatchOut(BaseModel):
    spawn_batch_id: int
    spawn_type: str
    strain_code: str
    vendor: Optional[str] = None
    lot_code: Optional[str] = None
    made_at: Optional[datetime] = None
    incubation_start_at: Optional[datetime] = None
    notes: Optional[str] = None
    class Config: from_attributes = True

class SubstrateBatchCreate(BaseModel):
    name: str = Field(..., description="Human label, used as bag ID prefix")
    substrate_recipe_version_id: int
    fill_profile_id: int
    bag_count: int
    mixed_at: Optional[datetime] = None
    mix_zone_id: Optional[int] = None
    incubation_zone_id: Optional[int] = None
    incubation_start_at: Optional[datetime] = None
    fruiting_zone_id: Optional[int] = None
    thermal_run_id: Optional[int] = None
    pasteurization_run_id: Optional[int] = None
    sample_moisture_wb_pct: Optional[float] = None
    sample_wet_weight_kg: Optional[float] = None
    notes: Optional[str] = None

class SubstrateBatchOut(SubstrateBatchCreate):
    substrate_batch_id: int
    class Config: from_attributes = True

class BatchInoculationCreate(BaseModel):
    substrate_batch_id: int
    spawn_batch_id: int
    inoculated_at: Optional[datetime] = None
    spawn_blocks_used: Optional[int] = None

class BatchInoculationUpdate(BaseModel):
    spawn_batch_id: Optional[int] = None
    inoculated_at: Optional[datetime] = None
    spawn_blocks_used: Optional[int] = None

class BatchInoculationOut(BaseModel):
    batch_inoculation_id: int
    substrate_batch_id: int
    spawn_batch_id: int
    inoculated_at: datetime
    spawn_blocks_used: Optional[int] = None
    class Config: from_attributes = True

class BatchInoculationDetailOut(BatchInoculationOut):
    spawn_batch: SpawnBatchOut

class SubstrateBagOut(BaseModel):
    bag_id: str
    substrate_batch_id: int
    created_at: datetime
    status: str
    class Config: from_attributes = True

class HarvestEventCreate(BaseModel):
    bag_id: str
    flush_number: int
    fresh_weight_kg: float
    harvested_at: Optional[datetime] = None
    notes: Optional[str] = None

class HarvestEventOut(HarvestEventCreate):
    harvest_event_id: int
    class Config: from_attributes = True

class BagDetailOut(SubstrateBagOut):
    harvest_events: List[HarvestEventOut] = []

class BatchMetricsOut(BaseModel):
    substrate_batch_id: int
    total_harvest_kg: float
    dry_kg_total: float
    be_percent: float

class PasteurizationRunCreate(BaseModel):
    run_code: str
    steam_start_at: Optional[datetime] = None
    steam_end_at: Optional[datetime] = None
    unloaded_at: datetime
    notes: Optional[str] = None

class PasteurizationRunUpdate(BaseModel):
    steam_start_at: Optional[datetime] = None
    steam_end_at: Optional[datetime] = None
    unloaded_at: Optional[datetime] = None
    notes: Optional[str] = None

class PasteurizationRunOut(BaseModel):
    pasteurization_run_id: int
    run_code: str
    steam_start_at: Optional[datetime] = None
    steam_end_at: Optional[datetime] = None
    unloaded_at: datetime
    notes: Optional[str] = None
    class Config: from_attributes = True
