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
  notes?: string | null;
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
