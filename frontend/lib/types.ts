export type FillProfile = {
  fill_profile_id: number;
  name: string;
  target_dry_kg_per_bag: number;
  target_water_kg_per_bag: number;
  notes?: string | null;
};

export type SubstrateRecipeVersion = {
  substrate_recipe_version_id: number;
  name: string;
  recipe_code: string;
  created_at: string;
  notes?: string | null;
};

export type SpawnRecipe = {
  spawn_recipe_id: number;
  recipe_code: string;
  notes?: string | null;
  created_at: string;
};

export type MixLot = {
  mix_lot_id: number;
  lot_code: string;
  substrate_recipe_version_id: number;
  fill_profile_id: number;
  mixed_at: string;
  notes?: string | null;
};

export type MushroomSpecies = {
  species_id: number;
  code: string;
  name: string;
  latin_name?: string | null;
  notes?: string | null;
  is_active: boolean;
};

export type GrainType = {
  grain_type_id: number;
  name: string;
  notes?: string | null;
};

export type PasteurizationRun = {
  pasteurization_run_id: number;
  run_code: string;
  mix_lot_id: number;
  substrate_recipe_version_id: number;
  steam_start_at?: string | null;
  steam_end_at?: string | null;
  unloaded_at: string;
  bag_count: number;
  notes?: string | null;
};

export type SterilizationRun = {
  sterilization_run_id: number;
  run_code: string;
  spawn_recipe_id: number;
  grain_type_id: number;
  cycle_start_at?: string | null;
  cycle_end_at?: string | null;
  unloaded_at: string;
  bag_count: number;
  temp_c?: number | null;
  psi?: number | null;
  hold_minutes?: number | null;
  notes?: string | null;
};

export type Bag = {
  bag_id: string;
  bag_type: "SPAWN" | "SUBSTRATE";
  species_id: number;
  pasteurization_run_id?: number | null;
  sterilization_run_id?: number | null;
  mix_lot_id?: number | null;
  substrate_recipe_version_id?: number | null;
  spawn_recipe_id?: number | null;
  grain_type_id?: number | null;
  parent_spawn_bag_id?: string | null;
  created_at: string;
  inoculated_at?: string | null;
  incubation_start_at?: string | null;
  fruiting_start_at?: string | null;
  disposed_at?: string | null;
  disposal_reason?: "CONTAMINATION" | "FINAL_HARVEST" | null;
  consumed_at?: string | null;
  status: string;
  notes?: string | null;
};

export type BagDetail = Bag & { harvest_events: HarvestEvent[] };

export type Inoculation = {
  inoculation_id: number;
  substrate_bag_id: string;
  spawn_bag_id: string;
  inoculated_at: string;
  notes?: string | null;
};

export type HarvestEvent = {
  harvest_event_id: number;
  bag_id: string;
  flush_number: 1 | 2;
  fresh_weight_kg: number;
  harvested_at: string;
  notes?: string | null;
};
