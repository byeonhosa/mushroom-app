import enum
from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Numeric, Text, Boolean, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class BagType(str, enum.Enum):
    SPAWN = "SPAWN"
    SUBSTRATE = "SUBSTRATE"


class DisposalReason(str, enum.Enum):
    CONTAMINATION = "CONTAMINATION"
    FINAL_HARVEST = "FINAL_HARVEST"


class InoculationSourceType(str, enum.Enum):
    LIQUID_CULTURE = "LIQUID_CULTURE"
    SPAWN_BAG = "SPAWN_BAG"


class BagStatusEventType(str, enum.Enum):
    CREATED = "CREATED"
    STERILIZED = "STERILIZED"
    PASTEURIZED = "PASTEURIZED"
    BAG_CODE_ASSIGNED = "BAG_CODE_ASSIGNED"
    INOCULATED = "INOCULATED"
    INCUBATION_STARTED = "INCUBATION_STARTED"
    READY = "READY"
    FRUITING_STARTED = "FRUITING_STARTED"
    HARVEST_RECORDED = "HARVEST_RECORDED"
    CONSUMED = "CONSUMED"
    DISPOSED = "DISPOSED"


class Zone(Base):
    __tablename__ = "zones"
    zone_id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    zone_type = Column(String(20), nullable=False)


class SubstrateRecipeVersion(Base):
    __tablename__ = "substrate_recipe_versions"
    substrate_recipe_version_id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    recipe_code = Column(String(20), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text)


class SpawnRecipe(Base):
    __tablename__ = "spawn_recipes"
    spawn_recipe_id = Column(Integer, primary_key=True)
    recipe_code = Column(String(40), nullable=False, unique=True)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FillProfile(Base):
    __tablename__ = "fill_profiles"
    fill_profile_id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    target_dry_kg_per_bag = Column(Numeric(10, 3), nullable=False)
    target_water_kg_per_bag = Column(Numeric(10, 3), nullable=False)
    notes = Column(Text)


class MixLot(Base):
    __tablename__ = "mix_lots"
    mix_lot_id = Column(Integer, primary_key=True)
    lot_code = Column(String(120), nullable=False, unique=True)
    substrate_recipe_version_id = Column(Integer, ForeignKey("substrate_recipe_versions.substrate_recipe_version_id"), nullable=False)
    fill_profile_id = Column(Integer, ForeignKey("fill_profiles.fill_profile_id"), nullable=False)
    mixed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text)

    substrate_recipe_version = relationship("SubstrateRecipeVersion")
    fill_profile = relationship("FillProfile")
    addins = relationship("MixLotAddin", back_populates="mix_lot", cascade="all, delete-orphan")


class Ingredient(Base):
    __tablename__ = "ingredients"
    ingredient_id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    category = Column(String(120))
    notes = Column(Text)

    lots = relationship("IngredientLot", back_populates="ingredient")


class IngredientLot(Base):
    __tablename__ = "ingredient_lots"
    ingredient_lot_id = Column(Integer, primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.ingredient_id"), nullable=False)
    vendor = Column(String(120))
    lot_code = Column(String(120))
    received_at = Column(DateTime(timezone=True))
    unit_cost_per_kg = Column(Numeric(12, 4))
    notes = Column(Text)

    ingredient = relationship("Ingredient", back_populates="lots")


class MixLotAddin(Base):
    __tablename__ = "mix_lot_addins"
    mix_lot_addin_id = Column(Integer, primary_key=True)
    mix_lot_id = Column(Integer, ForeignKey("mix_lots.mix_lot_id", ondelete="CASCADE"), nullable=False)
    ingredient_lot_id = Column(Integer, ForeignKey("ingredient_lots.ingredient_lot_id"), nullable=False)
    dry_kg = Column(Numeric(12, 4))
    pct_of_base_dry = Column(Numeric(8, 4))
    notes = Column(Text)

    mix_lot = relationship("MixLot", back_populates="addins")


class GrainType(Base):
    __tablename__ = "grain_types"
    grain_type_id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False, unique=True)
    notes = Column(Text)


class MushroomSpecies(Base):
    __tablename__ = "mushroom_species"
    species_id = Column(Integer, primary_key=True)
    code = Column(String(40), nullable=False, unique=True)
    name = Column(String(120), nullable=False)
    latin_name = Column(String(160))
    notes = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)


class LiquidCulture(Base):
    __tablename__ = "liquid_cultures"
    liquid_culture_id = Column(Integer, primary_key=True)
    culture_code = Column(String(120), nullable=False, unique=True)
    species_id = Column(Integer, ForeignKey("mushroom_species.species_id"), nullable=False)
    source = Column(String(160))
    prepared_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)

    species = relationship("MushroomSpecies")


class PasteurizationRun(Base):
    __tablename__ = "pasteurization_runs"
    pasteurization_run_id = Column(Integer, primary_key=True)
    run_code = Column(String(120), nullable=False, unique=True)
    mix_lot_id = Column(Integer, ForeignKey("mix_lots.mix_lot_id"), nullable=False)
    substrate_recipe_version_id = Column(Integer, ForeignKey("substrate_recipe_versions.substrate_recipe_version_id"), nullable=False)
    steam_start_at = Column(DateTime(timezone=True))
    steam_end_at = Column(DateTime(timezone=True))
    unloaded_at = Column(DateTime(timezone=True), nullable=False)
    bag_count = Column(Integer, nullable=False)
    notes = Column(Text)

    mix_lot = relationship("MixLot")
    substrate_recipe_version = relationship("SubstrateRecipeVersion")


class SterilizationRun(Base):
    __tablename__ = "sterilization_runs"
    sterilization_run_id = Column(Integer, primary_key=True)
    run_code = Column(String(120), nullable=False, unique=True)
    spawn_recipe_id = Column(Integer, ForeignKey("spawn_recipes.spawn_recipe_id"), nullable=False)
    grain_type_id = Column(Integer, ForeignKey("grain_types.grain_type_id"), nullable=False)
    cycle_start_at = Column(DateTime(timezone=True))
    cycle_end_at = Column(DateTime(timezone=True))
    unloaded_at = Column(DateTime(timezone=True), nullable=False)
    bag_count = Column(Integer, nullable=False)
    temp_c = Column(Numeric(6, 2))
    psi = Column(Numeric(6, 2))
    hold_minutes = Column(Integer)
    notes = Column(Text)

    spawn_recipe = relationship("SpawnRecipe")
    grain_type = relationship("GrainType")


class Bag(Base):
    __tablename__ = "bags"
    bag_id = Column(String(80), primary_key=True)
    bag_code = Column(String(120), unique=True)
    bag_type = Column(String(20), nullable=False)  # SPAWN or SUBSTRATE
    species_id = Column(Integer, ForeignKey("mushroom_species.species_id"), nullable=True)
    pasteurization_run_id = Column(Integer, ForeignKey("pasteurization_runs.pasteurization_run_id", ondelete="SET NULL"))
    sterilization_run_id = Column(Integer, ForeignKey("sterilization_runs.sterilization_run_id", ondelete="SET NULL"))
    mix_lot_id = Column(Integer, ForeignKey("mix_lots.mix_lot_id", ondelete="SET NULL"))
    substrate_recipe_version_id = Column(Integer, ForeignKey("substrate_recipe_versions.substrate_recipe_version_id", ondelete="SET NULL"))
    spawn_recipe_id = Column(Integer, ForeignKey("spawn_recipes.spawn_recipe_id", ondelete="SET NULL"))
    grain_type_id = Column(Integer, ForeignKey("grain_types.grain_type_id", ondelete="SET NULL"))
    parent_spawn_bag_id = Column(String(80), ForeignKey("bags.bag_id", ondelete="SET NULL"))
    source_liquid_culture_id = Column(Integer, ForeignKey("liquid_cultures.liquid_culture_id", ondelete="SET NULL"))
    target_dry_kg = Column(Numeric(10, 3))
    actual_dry_kg = Column(Numeric(10, 3))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    labeled_at = Column(DateTime(timezone=True))
    inoculated_at = Column(DateTime(timezone=True))
    incubation_start_at = Column(DateTime(timezone=True))
    ready_at = Column(DateTime(timezone=True))
    fruiting_start_at = Column(DateTime(timezone=True))
    disposed_at = Column(DateTime(timezone=True))
    disposal_reason = Column(String(20))
    consumed_at = Column(DateTime(timezone=True))
    status = Column(String(40), nullable=False, default="FILLED")
    notes = Column(Text)

    species = relationship("MushroomSpecies")
    pasteurization_run = relationship("PasteurizationRun")
    sterilization_run = relationship("SterilizationRun")
    mix_lot = relationship("MixLot")
    substrate_recipe_version = relationship("SubstrateRecipeVersion")
    spawn_recipe = relationship("SpawnRecipe")
    grain_type = relationship("GrainType")
    parent_spawn_bag = relationship("Bag", remote_side=[bag_id])
    source_liquid_culture = relationship("LiquidCulture", foreign_keys=[source_liquid_culture_id])
    inoculation = relationship(
        "Inoculation",
        back_populates="substrate_bag",
        uselist=False,
        primaryjoin="Bag.bag_id == Inoculation.substrate_bag_id",
        foreign_keys="Inoculation.substrate_bag_id",
    )
    inoculation_batch_targets = relationship(
        "InoculationBatchTarget",
        back_populates="bag",
        cascade="all, delete-orphan",
    )
    harvest_events = relationship("HarvestEvent", back_populates="bag", cascade="all, delete-orphan")
    status_events = relationship("BagStatusEvent", back_populates="bag", cascade="all, delete-orphan")

    @property
    def bag_ref(self) -> str:
        return self.bag_code or self.bag_id

    @property
    def parent_spawn_bag_ref(self) -> str | None:
        if not self.parent_spawn_bag:
            return None
        return self.parent_spawn_bag.bag_ref

    @property
    def inoculation_source_type(self) -> str | None:
        if self.parent_spawn_bag_id:
            return InoculationSourceType.SPAWN_BAG.value
        if self.source_liquid_culture_id:
            return InoculationSourceType.LIQUID_CULTURE.value
        return None

    @property
    def source_spawn_bag_id(self) -> str | None:
        return self.parent_spawn_bag_id

    @property
    def source_spawn_bag_ref(self) -> str | None:
        return self.parent_spawn_bag_ref

    @property
    def source_liquid_culture_code(self) -> str | None:
        if not self.source_liquid_culture:
            return None
        return self.source_liquid_culture.culture_code

    @property
    def dry_weight_kg(self) -> float | None:
        if self.actual_dry_kg is not None:
            return float(self.actual_dry_kg)
        if self.target_dry_kg is not None:
            return float(self.target_dry_kg)
        return None

    @property
    def dry_weight_source(self) -> str | None:
        if self.actual_dry_kg is not None:
            return "ACTUAL"
        if self.target_dry_kg is not None:
            return "TARGET"
        return None

    @property
    def total_harvest_kg(self) -> float:
        return sum(float(event.fresh_weight_kg) for event in self.harvest_events)

    @property
    def bio_efficiency(self) -> float | None:
        dry_weight = self.dry_weight_kg
        if self.bag_type != "SUBSTRATE" or dry_weight is None or dry_weight <= 0:
            return None
        return self.total_harvest_kg / dry_weight


class BagStatusEvent(Base):
    __tablename__ = "bag_status_events"
    bag_status_event_id = Column(Integer, primary_key=True)
    bag_id = Column(String(80), ForeignKey("bags.bag_id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(40), nullable=False)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    detail = Column(Text)
    notes = Column(Text)

    bag = relationship("Bag", back_populates="status_events")


class InoculationBatch(Base):
    __tablename__ = "inoculation_batches"
    inoculation_batch_id = Column(Integer, primary_key=True)
    source_type = Column(String(20), nullable=False)
    source_spawn_bag_id = Column(String(80), ForeignKey("bags.bag_id", ondelete="SET NULL"))
    source_liquid_culture_id = Column(Integer, ForeignKey("liquid_cultures.liquid_culture_id", ondelete="SET NULL"))
    species_id = Column(Integer, ForeignKey("mushroom_species.species_id", ondelete="SET NULL"))
    inoculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text)

    source_spawn_bag = relationship("Bag", foreign_keys=[source_spawn_bag_id])
    source_liquid_culture = relationship("LiquidCulture", foreign_keys=[source_liquid_culture_id])
    species = relationship("MushroomSpecies")
    targets = relationship(
        "InoculationBatchTarget",
        back_populates="inoculation_batch",
        cascade="all, delete-orphan",
    )


class InoculationBatchTarget(Base):
    __tablename__ = "inoculation_batch_targets"
    inoculation_batch_target_id = Column(Integer, primary_key=True)
    inoculation_batch_id = Column(Integer, ForeignKey("inoculation_batches.inoculation_batch_id", ondelete="CASCADE"), nullable=False)
    bag_id = Column(String(80), ForeignKey("bags.bag_id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("bag_id", name="uq_inoculation_batch_targets_bag"),
    )

    inoculation_batch = relationship("InoculationBatch", back_populates="targets")
    bag = relationship("Bag", back_populates="inoculation_batch_targets")


class Inoculation(Base):
    __tablename__ = "inoculations"
    inoculation_id = Column(Integer, primary_key=True)
    substrate_bag_id = Column(String(80), ForeignKey("bags.bag_id", ondelete="CASCADE"), nullable=False, unique=True)
    spawn_bag_id = Column(String(80), ForeignKey("bags.bag_id", ondelete="RESTRICT"), nullable=False)
    inoculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text)

    substrate_bag = relationship("Bag", foreign_keys=[substrate_bag_id], back_populates="inoculation")
    spawn_bag = relationship("Bag", foreign_keys=[spawn_bag_id])

    @property
    def substrate_bag_ref(self) -> str:
        if self.substrate_bag:
            return self.substrate_bag.bag_ref
        return self.substrate_bag_id

    @property
    def spawn_bag_ref(self) -> str:
        if self.spawn_bag:
            return self.spawn_bag.bag_ref
        return self.spawn_bag_id


class HarvestEvent(Base):
    __tablename__ = "harvest_events"
    harvest_event_id = Column(Integer, primary_key=True)
    bag_id = Column(String(80), ForeignKey("bags.bag_id", ondelete="CASCADE"), nullable=False)
    flush_number = Column(Integer, nullable=False)
    fresh_weight_kg = Column(Numeric(10, 3), nullable=False)
    harvested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text)

    __table_args__ = (
        UniqueConstraint("bag_id", "flush_number", name="uq_harvest_events_bag_flush"),
    )

    bag = relationship("Bag", back_populates="harvest_events")

    @property
    def bag_ref(self) -> str:
        if self.bag:
            return self.bag.bag_ref
        return self.bag_id


class SpeciesProfile(Base):
    """Species cultivation reference (Crowe-detailed commercial parameters).

    Standalone reference table — NOT the operational ``mushroom_species`` table
    that carries FKs from liquid_cultures/bags. Field names mirror the keys in
    backend/app/seeds/mushroom_species.json; the JSON ``id`` maps to ``code``,
    which is the upsert key used by ``app.seed_species``.

    Range fields are nullable integers (``*_low`` / ``*_high``); a JSON null is
    preserved as SQL NULL, never coerced to 0. ``use_type`` and
    ``pinning_trigger`` are effectively enums whose allowed values come from the
    JSON _meta.conventions:
      use_type:        culinary | medicinal | both
      pinning_trigger: fae_increase | temp_drop | co2_drop | co2_drop_cold_shock
                       | cold_shock_and_strike | combined | form_dependent
    """

    __tablename__ = "species_profiles"

    species_profile_id = Column(Integer, primary_key=True)
    code = Column(String(60), nullable=False, unique=True)
    common_name = Column(String(160), nullable=False)
    scientific_name = Column(String(160))
    difficulty = Column(String(40))
    difficulty_rank = Column(Integer)
    use_type = Column(String(20))
    substrate_primary = Column(Text)
    substrate_moisture_pct_low = Column(Integer)
    substrate_moisture_pct_high = Column(Integer)
    spawn_rate_pct_low = Column(Integer)
    spawn_rate_pct_high = Column(Integer)
    incubation_temp_f_low = Column(Integer)
    incubation_temp_f_high = Column(Integer)
    colonization_days_low = Column(Integer)
    colonization_days_high = Column(Integer)
    fruiting_temp_f_low = Column(Integer)
    fruiting_temp_f_high = Column(Integer)
    fruiting_humidity_pct_low = Column(Integer)
    fruiting_humidity_pct_high = Column(Integer)
    fruiting_co2_ppm_low = Column(Integer)
    fruiting_co2_ppm_high = Column(Integer)
    fae_ach_low = Column(Integer)
    fae_ach_high = Column(Integer)
    light_lux_low = Column(Integer)
    light_lux_high = Column(Integer)
    light_hours_per_day_low = Column(Integer)
    light_hours_per_day_high = Column(Integer)
    pinning_trigger = Column(String(40))
    pin_to_harvest_days_low = Column(Integer)
    pin_to_harvest_days_high = Column(Integer)
    biological_efficiency_pct_low = Column(Integer)
    biological_efficiency_pct_high = Column(Integer)
    typical_flushes_low = Column(Integer)
    typical_flushes_high = Column(Integer)
    yield_notes = Column(Text)
    pricing_notes = Column(Text)
    notes = Column(Text)
