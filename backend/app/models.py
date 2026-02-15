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
    incubation_zone_id = Column(Integer, ForeignKey("zones.zone_id"), nullable=True)
    notes = Column(Text)

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
    bag_id = Column(String(64), ForeignKey("substrate_bags.bag_id"), nullable=False)
    harvested_at = Column(DateTime(timezone=True), server_default=func.now())
    flush_number = Column(Integer, nullable=False)
    fresh_weight_kg = Column(Numeric(10, 3), nullable=False)
    notes = Column(Text)

    __table_args__ = (
        CheckConstraint("flush_number IN (1,2)", name="ck_flush_number_1_2"),
    )

    bag = relationship("SubstrateBag", back_populates="harvest_events")
