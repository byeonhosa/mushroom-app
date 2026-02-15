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

export type PasteurizationRun = {
  pasteurization_run_id: number;
  run_code: string;
  steam_start_at?: string | null;
  steam_end_at?: string | null;
  unloaded_at: string;
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
  grain_dry_kg?: number | null;
  grain_water_kg?: number | null;
  supplement_kg?: number | null;
  lc_vendor?: string | null;
  lc_code?: string | null;
  sterilization_run_code?: string | null;
  incubation_zone_id?: number | null;
  notes?: string | null;
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
  bag_id: string;
  flush_number: 1 | 2;
  fresh_weight_kg: number;
  harvested_at: string;
  notes?: string | null;
};

export type BagDetail = SubstrateBag & { harvest_events: HarvestEvent[] };

export type BatchMetrics = {
  substrate_batch_id: number;
  total_harvest_kg: number;
  dry_kg_total: number;
  be_percent: number;
};
