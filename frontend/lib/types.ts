export type FillProfile = {
  fill_profile_id: number;
  name: string;
  target_dry_kg_per_bag: number;
  target_water_kg_per_bag: number;
  notes?: string | null;
};

export type SubstrateBatch = {
  substrate_batch_id: number;
  name: string;
  substrate_recipe_version_id: number;
  fill_profile_id: number;
  bag_count: number;
  pasteurization_run_id?: number | null;
  notes?: string | null;
};

export type Batch = SubstrateBatch;

export type MixLot = {
  mix_lot_id: number;
  lot_code: string;
  notes?: string | null;
  created_at: string;
};

export type SpawnRecipe = {
  spawn_recipe_id: number;
  recipe_code: string;
  notes?: string | null;
  created_at: string;
};

export type MushroomSpecies = {
  species_id: number;
  code: string;
  name: string;
  latin_name?: string | null;
  notes?: string | null;
  is_active: boolean;
};

export type PasteurizationRun = {
  pasteurization_run_id: number;
  run_code: string;
  steam_start_at?: string | null;
  steam_end_at?: string | null;
  unloaded_at: string;
  notes?: string | null;
};

export type SterilizationRun = {
  sterilization_run_id: number;
  run_code: string;
  cycle_start_at?: string | null;
  cycle_end_at?: string | null;
  unloaded_at: string;
  temp_c?: number | null;
  psi?: number | null;
  hold_minutes?: number | null;
  notes?: string | null;
};

export type GrainType = {
  grain_type_id: number;
  name: string;
  notes?: string | null;
};

export type SpawnBatch = {
  spawn_batch_id: number;
  spawn_type: "PURCHASED_BLOCK" | "IN_HOUSE_GRAIN";
  strain_code: string;
  vendor?: string | null;
  lot_code?: string | null;
  made_at?: string | null;
  incubation_start_at?: string | null;
  sterilization_run_id?: number | null;
  grain_type_id?: number | null;
  grain_kg?: number | null;
  vermiculite_kg?: number | null;
  water_kg?: number | null;
  supplement_kg?: number | null;
  hydration_ratio?: number | null;
  expected_added_water_wb_pct?: number | null;
  notes?: string | null;
};

export type Ingredient = {
  ingredient_id: number;
  name: string;
  category?: string | null;
  notes?: string | null;
};

export type IngredientLot = {
  ingredient_lot_id: number;
  ingredient_id: number;
  vendor?: string | null;
  lot_code?: string | null;
  received_at?: string | null;
  unit_cost_per_kg?: number | null;
  notes?: string | null;
  ingredient?: Ingredient | null;
};

export type SubstrateBatchAddin = {
  substrate_batch_addin_id: number;
  substrate_batch_id: number;
  ingredient_lot_id: number;
  dry_kg?: number | null;
  pct_of_base_dry?: number | null;
  notes?: string | null;
  ingredient_lot: IngredientLot;
};

export type BatchInoculation = {
  batch_inoculation_id: number;
  substrate_batch_id: number;
  spawn_batch_id: number;
  inoculated_at: string;
  spawn_blocks_used?: number | null;
  spawn_batch: SpawnBatch;
};

export type SubstrateBag = {
  bag_id: string;
  substrate_batch_id: number;
  status: string;
  created_at: string;
};

export type HarvestEvent = {
  harvest_event_id: number;
  block_id?: number | null;
  bag_id?: string | null;
  flush_number: 1 | 2;
  fresh_weight_kg: number;
  harvested_at: string;
  notes?: string | null;
};

export type Block = {
  block_id: number;
  block_code: string;
  block_type: "SPAWN" | "SUBSTRATE";
  species_id: number;
  mix_lot_id?: number | null;
  pasteurization_run_id?: number | null;
  sterilization_run_id?: number | null;
  spawn_recipe_id?: number | null;
  substrate_batch_id?: number | null;
  spawn_batch_id?: number | null;
  status?: string | null;
  notes?: string | null;
  created_at: string;
};

export type Inoculation = {
  inoculation_id: number;
  child_block_id: number;
  parent_spawn_block_id: number;
  inoculated_at: string;
  notes?: string | null;
  child_block_code?: string | null;
  parent_spawn_block_code?: string | null;
};

export type BagDetail = SubstrateBag & { harvest_events: HarvestEvent[] };

export type BatchMetrics = {
  substrate_batch_id: number;
  total_harvest_kg: number;
  dry_kg_total: number;
  be_percent: number;
};
