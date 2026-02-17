import enum
from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Numeric, Text, Enum, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class ZoneType(str, enum.Enum):
    INCUBATION = "INCUBATION"
    FRUITING = "FRUITING"
    MIXING = "MIXING"
    OTHER = "OTHER"

class SpawnType(str, enum.Enum):
    PURCHASED_BLOCK = "PURCHASED_BLOCK"
    IN_HOUSE_GRAIN = "IN_HOUSE_GRAIN"

class ThermalProcessType(str, enum.Enum):
    PASTEURIZATION_STEAM = "PASTEURIZATION_STEAM"
    STERILIZATION_AUTOCLAVE = "STERILIZATION_AUTOCLAVE"

class Zone(Base):
    __tablename__ = "zones"
    zone_id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    zone_type = Column(Enum(ZoneType), nullable=False, default=ZoneType.OTHER)

class FillProfile(Base):
    __tablename__ = "fill_profiles"
    fill_profile_id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    target_dry_kg_per_bag = Column(Numeric(10, 3), nullable=False)
    target_water_kg_per_bag = Column(Numeric(10, 3), nullable=False)
    notes = Column(Text)

class SubstrateRecipeVersion(Base):
    __tablename__ = "substrate_recipe_versions"
    substrate_recipe_version_id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)

class MixLot(Base):
    __tablename__ = "mix_lots"
    mix_lot_id = Column(Integer, primary_key=True)
    lot_code = Column(String(120), nullable=False, unique=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class SpawnRecipe(Base):
    __tablename__ = "spawn_recipes"
    spawn_recipe_id = Column(Integer, primary_key=True)
    recipe_code = Column(String(120), nullable=False, unique=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Ingredient(Base):
    __tablename__ = "ingredients"
    ingredient_id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    category = Column(String(120), nullable=True)
    notes = Column(Text, nullable=True)

    lots = relationship("IngredientLot", back_populates="ingredient")

class IngredientLot(Base):
    __tablename__ = "ingredient_lots"
    ingredient_lot_id = Column(Integer, primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.ingredient_id"), nullable=False)
    vendor = Column(String(120), nullable=True)
    lot_code = Column(String(120), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    unit_cost_per_kg = Column(Numeric(12, 4), nullable=True)
    notes = Column(Text, nullable=True)

    ingredient = relationship("Ingredient", back_populates="lots")
    batch_addins = relationship("SubstrateBatchAddin", back_populates="ingredient_lot")

class ThermalRun(Base):
    __tablename__ = "thermal_runs"
    thermal_run_id = Column(Integer, primary_key=True)
    process_type = Column(Enum(ThermalProcessType), nullable=False)
    unloaded_at = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text)

class PasteurizationRun(Base):
    __tablename__ = "pasteurization_runs"
    pasteurization_run_id = Column(Integer, primary_key=True)
    run_code = Column(String(120), nullable=False, unique=True)
    steam_start_at = Column(DateTime(timezone=True), nullable=True)
    steam_end_at = Column(DateTime(timezone=True), nullable=True)
    unloaded_at = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text)

class SterilizationRun(Base):
    __tablename__ = "sterilization_runs"
    sterilization_run_id = Column(Integer, primary_key=True)
    run_code = Column(String(120), nullable=False, unique=True)
    cycle_start_at = Column(DateTime(timezone=True), nullable=True)
    cycle_end_at = Column(DateTime(timezone=True), nullable=True)
    unloaded_at = Column(DateTime(timezone=True), nullable=False)
    temp_c = Column(Numeric(6, 2), nullable=True)
    psi = Column(Numeric(6, 2), nullable=True)
    hold_minutes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

class GrainType(Base):
    __tablename__ = "grain_types"
    grain_type_id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False, unique=True)
    notes = Column(Text, nullable=True)

class Block(Base):
    __tablename__ = "blocks"
    block_id = Column(Integer, primary_key=True)
    block_code = Column(String(120), nullable=False, unique=True)
    block_type = Column(String(20), nullable=False)
    mix_lot_id = Column(Integer, ForeignKey("mix_lots.mix_lot_id", ondelete="SET NULL"), nullable=True)
    pasteurization_run_id = Column(Integer, ForeignKey("pasteurization_runs.pasteurization_run_id", ondelete="SET NULL"), nullable=True)
    sterilization_run_id = Column(Integer, ForeignKey("sterilization_runs.sterilization_run_id", ondelete="SET NULL"), nullable=True)
    spawn_recipe_id = Column(Integer, ForeignKey("spawn_recipes.spawn_recipe_id", ondelete="SET NULL"), nullable=True)
    substrate_batch_id = Column(Integer, ForeignKey("substrate_batches.substrate_batch_id", ondelete="SET NULL"), nullable=True)
    spawn_batch_id = Column(Integer, ForeignKey("spawn_batches.spawn_batch_id", ondelete="SET NULL"), nullable=True)
    status = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    mix_lot = relationship("MixLot")
    pasteurization_run = relationship("PasteurizationRun")
    sterilization_run = relationship("SterilizationRun")
    spawn_recipe = relationship("SpawnRecipe")
    substrate_batch = relationship("SubstrateBatch")
    spawn_batch = relationship("SpawnBatch")

class Inoculation(Base):
    __tablename__ = "inoculations"
    inoculation_id = Column(Integer, primary_key=True)
    child_block_id = Column(Integer, ForeignKey("blocks.block_id", ondelete="CASCADE"), nullable=False)
    parent_spawn_block_id = Column(Integer, ForeignKey("blocks.block_id", ondelete="RESTRICT"), nullable=False)
    inoculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("child_block_id", name="uq_inoculations_child_block_id"),
    )

    child_block = relationship("Block", foreign_keys=[child_block_id])
    parent_spawn_block = relationship("Block", foreign_keys=[parent_spawn_block_id])

class SpawnBatch(Base):
    __tablename__ = "spawn_batches"
    spawn_batch_id = Column(Integer, primary_key=True)
    spawn_type = Column(Enum(SpawnType), nullable=False)
    strain_code = Column(String(30), nullable=False)
    vendor = Column(String(120), nullable=True)
    lot_code = Column(String(120), nullable=True)
    made_at = Column(DateTime(timezone=True), nullable=True)
    incubation_start_at = Column(DateTime(timezone=True), nullable=True)
    grain_dry_kg = Column(Numeric(10, 3), nullable=True)
    grain_water_kg = Column(Numeric(10, 3), nullable=True)
    supplement_kg = Column(Numeric(10, 3), nullable=True)
    lc_vendor = Column(String(120), nullable=True)
    lc_code = Column(String(120), nullable=True)
    sterilization_run_code = Column(String(120), nullable=True)
    sterilization_run_id = Column(Integer, ForeignKey("sterilization_runs.sterilization_run_id"), nullable=True)
    grain_type_id = Column(Integer, ForeignKey("grain_types.grain_type_id"), nullable=True)
    grain_kg = Column(Numeric(10, 3), nullable=True)
    vermiculite_kg = Column(Numeric(10, 3), nullable=True)
    water_kg = Column(Numeric(10, 3), nullable=True)
    incubation_zone_id = Column(Integer, ForeignKey("zones.zone_id"), nullable=True)
    notes = Column(Text)

    sterilization_run = relationship("SterilizationRun")
    grain_type = relationship("GrainType")

class SubstrateBatch(Base):
    __tablename__ = "substrate_batches"
    substrate_batch_id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    substrate_recipe_version_id = Column(Integer, ForeignKey("substrate_recipe_versions.substrate_recipe_version_id"), nullable=False)
    fill_profile_id = Column(Integer, ForeignKey("fill_profiles.fill_profile_id"), nullable=False)
    bag_count = Column(Integer, nullable=False)

    mixed_at = Column(DateTime(timezone=True), server_default=func.now())
    mix_zone_id = Column(Integer, ForeignKey("zones.zone_id"), nullable=True)

    incubation_zone_id = Column(Integer, ForeignKey("zones.zone_id"), nullable=True)
    incubation_start_at = Column(DateTime(timezone=True), nullable=True)
    fruiting_zone_id = Column(Integer, ForeignKey("zones.zone_id"), nullable=True)

    thermal_run_id = Column(Integer, ForeignKey("thermal_runs.thermal_run_id"), nullable=True)
    pasteurization_run_id = Column(Integer, ForeignKey("pasteurization_runs.pasteurization_run_id"), nullable=True)

    sample_moisture_wb_pct = Column(Numeric(6, 3), nullable=True)
    sample_wet_weight_kg = Column(Numeric(10, 3), nullable=True)

    notes = Column(Text)

    recipe = relationship("SubstrateRecipeVersion")
    fill_profile = relationship("FillProfile")
    inoculation = relationship("BatchInoculation", back_populates="substrate_batch", uselist=False)
    bags = relationship("SubstrateBag", back_populates="batch", cascade="all, delete-orphan")
    addins = relationship("SubstrateBatchAddin", back_populates="substrate_batch", cascade="all, delete-orphan")

class SubstrateBatchAddin(Base):
    __tablename__ = "substrate_batch_addins"
    substrate_batch_addin_id = Column(Integer, primary_key=True)
    substrate_batch_id = Column(Integer, ForeignKey("substrate_batches.substrate_batch_id", ondelete="CASCADE"), nullable=False)
    ingredient_lot_id = Column(Integer, ForeignKey("ingredient_lots.ingredient_lot_id"), nullable=False)
    dry_kg = Column(Numeric(12, 4), nullable=True)
    pct_of_base_dry = Column(Numeric(8, 4), nullable=True)
    notes = Column(Text, nullable=True)

    substrate_batch = relationship("SubstrateBatch", back_populates="addins")
    ingredient_lot = relationship("IngredientLot", back_populates="batch_addins")

class BatchInoculation(Base):
    __tablename__ = "batch_inoculations"
    batch_inoculation_id = Column(Integer, primary_key=True)
    substrate_batch_id = Column(Integer, ForeignKey("substrate_batches.substrate_batch_id"), nullable=False)
    spawn_batch_id = Column(Integer, ForeignKey("spawn_batches.spawn_batch_id"), nullable=False)
    inoculated_at = Column(DateTime(timezone=True), server_default=func.now())
    spawn_blocks_used = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("substrate_batch_id", name="uq_batch_inoculations_substrate_batch_id"),
    )

    spawn_batch = relationship("SpawnBatch")
    substrate_batch = relationship("SubstrateBatch", back_populates="inoculation")

class SubstrateBag(Base):
    __tablename__ = "substrate_bags"
    bag_id = Column(String(64), primary_key=True)
    substrate_batch_id = Column(Integer, ForeignKey("substrate_batches.substrate_batch_id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(40), nullable=False, default="INCUBATING")

    batch = relationship("SubstrateBatch", back_populates="bags")
    harvest_events = relationship("HarvestEvent", back_populates="bag", cascade="all, delete-orphan")

class HarvestEvent(Base):
    __tablename__ = "harvest_events"
    harvest_event_id = Column(Integer, primary_key=True)
    bag_id = Column(String(64), ForeignKey("substrate_bags.bag_id"), nullable=True)
    block_id = Column(Integer, ForeignKey("blocks.block_id"), nullable=True)
    harvested_at = Column(DateTime(timezone=True), server_default=func.now())
    flush_number = Column(Integer, nullable=False)
    fresh_weight_kg = Column(Numeric(10, 3), nullable=False)
    notes = Column(Text)

    __table_args__ = (
        CheckConstraint("flush_number IN (1,2)", name="ck_flush_number_1_2"),
    )

    bag = relationship("SubstrateBag", back_populates="harvest_events")
    block = relationship("Block")
