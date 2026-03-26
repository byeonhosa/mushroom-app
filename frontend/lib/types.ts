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

export type LiquidCulture = {
  liquid_culture_id: number;
  culture_code: string;
  species_id: number;
  source?: string | null;
  prepared_at?: string | null;
  created_at: string;
  notes?: string | null;
  is_active: boolean;
};

export type GrainType = {
  grain_type_id: number;
  name: string;
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
  bag_code?: string | null;
  bag_ref: string;
  bag_type: "SPAWN" | "SUBSTRATE";
  species_id?: number | null;
  pasteurization_run_id?: number | null;
  sterilization_run_id?: number | null;
  mix_lot_id?: number | null;
  substrate_recipe_version_id?: number | null;
  spawn_recipe_id?: number | null;
  grain_type_id?: number | null;
  parent_spawn_bag_id?: string | null;
  parent_spawn_bag_ref?: string | null;
  source_spawn_bag_id?: string | null;
  source_spawn_bag_ref?: string | null;
  source_liquid_culture_id?: number | null;
  source_liquid_culture_code?: string | null;
  inoculation_source_type?: "LIQUID_CULTURE" | "SPAWN_BAG" | null;
  target_dry_kg?: number | null;
  actual_dry_kg?: number | null;
  dry_weight_kg?: number | null;
  dry_weight_source?: "ACTUAL" | "TARGET" | null;
  bio_efficiency?: number | null;
  created_at: string;
  labeled_at?: string | null;
  inoculated_at?: string | null;
  incubation_start_at?: string | null;
  ready_at?: string | null;
  fruiting_start_at?: string | null;
  disposed_at?: string | null;
  disposal_reason?: "CONTAMINATION" | "FINAL_HARVEST" | null;
  consumed_at?: string | null;
  status: string;
  notes?: string | null;
};

export type BagStatusEvent = {
  bag_status_event_id: number;
  bag_id: string;
  event_type:
    | "CREATED"
    | "STERILIZED"
    | "PASTEURIZED"
    | "BAG_CODE_ASSIGNED"
    | "INOCULATED"
    | "INCUBATION_STARTED"
    | "READY"
    | "FRUITING_STARTED"
    | "HARVEST_RECORDED"
    | "CONSUMED"
    | "DISPOSED";
  occurred_at: string;
  detail?: string | null;
  notes?: string | null;
};

export type LineageChildBag = {
  generation: number;
  bag_id: string;
  bag_code?: string | null;
  bag_ref: string;
  bag_type: "SPAWN" | "SUBSTRATE";
  status: string;
  disposal_reason?: "CONTAMINATION" | "FINAL_HARVEST" | null;
  species_id?: number | null;
  species_code?: string | null;
  species_name?: string | null;
  sterilization_run_id?: number | null;
  sterilization_run_code?: string | null;
  pasteurization_run_id?: number | null;
  pasteurization_run_code?: string | null;
  parent_spawn_bag_id?: string | null;
  parent_spawn_bag_ref?: string | null;
  source_liquid_culture_id?: number | null;
  source_liquid_culture_code?: string | null;
  inoculation_source_type?: "LIQUID_CULTURE" | "SPAWN_BAG" | null;
  source_sterilization_run_id?: number | null;
  source_sterilization_run_code?: string | null;
  target_dry_kg?: number | null;
  actual_dry_kg?: number | null;
  dry_weight_kg?: number | null;
  dry_weight_source?: "ACTUAL" | "TARGET" | null;
  total_harvest_kg: number;
  bio_efficiency?: number | null;
  contaminated: boolean;
};

export type BagCollectionSummary = {
  total_bags: number;
  unlabeled_bags: number;
  inoculated_bags: number;
  ready_bags: number;
  fruiting_bags: number;
  contaminated_bags: number;
  harvested_bags: number;
  consumed_bags: number;
  total_harvest_kg: number;
  total_dry_weight_kg: number;
  overall_bio_efficiency?: number | null;
};

export type BagDetail = Bag & {
  status_events: BagStatusEvent[];
  harvest_events: HarvestEvent[];
  child_bags: LineageChildBag[];
  child_summary?: BagCollectionSummary | null;
};

export type Inoculation = {
  inoculation_id: number;
  substrate_bag_id: string;
  substrate_bag_ref: string;
  spawn_bag_id: string;
  spawn_bag_ref: string;
  inoculated_at: string;
  notes?: string | null;
};

export type HarvestEvent = {
  harvest_event_id: number;
  bag_id: string;
  bag_ref: string;
  flush_number: 1 | 2;
  fresh_weight_kg: number;
  harvested_at: string;
  notes?: string | null;
};

export type ReportGroup = {
  key: string;
  label: string;
  total_bags: number;
  contaminated_bags: number;
  contamination_rate: number;
};

export type PasteurizationRunMetrics = {
  pasteurization_run_id: number;
  run_code: string;
  total_bags: number;
  contaminated_bags: number;
  contamination_rate: number;
  total_harvest_kg: number;
  total_dry_weight_kg: number;
  bio_efficiency?: number | null;
};

export type SubstrateBagMetrics = {
  bag_id: string;
  bag_code?: string | null;
  bag_ref: string;
  status: string;
  disposal_reason?: "CONTAMINATION" | "FINAL_HARVEST" | null;
  species_id?: number | null;
  species_code?: string | null;
  species_name?: string | null;
  pasteurization_run_id?: number | null;
  pasteurization_run_code?: string | null;
  parent_spawn_bag_id?: string | null;
  parent_spawn_bag_ref?: string | null;
  source_liquid_culture_id?: number | null;
  source_liquid_culture_code?: string | null;
  spawn_generation?: number | null;
  source_sterilization_run_id?: number | null;
  source_sterilization_run_code?: string | null;
  target_dry_kg?: number | null;
  actual_dry_kg?: number | null;
  dry_weight_kg?: number | null;
  dry_weight_source?: "ACTUAL" | "TARGET" | null;
  total_harvest_kg: number;
  bio_efficiency?: number | null;
  contaminated: boolean;
};

export type ContaminationCase = {
  bag_id: string;
  bag_code?: string | null;
  bag_ref: string;
  bag_type: "SPAWN" | "SUBSTRATE";
  status: string;
  disposal_reason?: "CONTAMINATION" | "FINAL_HARVEST" | null;
  contaminated_at?: string | null;
  species_id?: number | null;
  species_code?: string | null;
  species_name?: string | null;
  sterilization_run_id?: number | null;
  sterilization_run_code?: string | null;
  pasteurization_run_id?: number | null;
  pasteurization_run_code?: string | null;
  parent_spawn_bag_id?: string | null;
  parent_spawn_bag_ref?: string | null;
  source_liquid_culture_id?: number | null;
  source_liquid_culture_code?: string | null;
  spawn_generation?: number | null;
  source_sterilization_run_id?: number | null;
  source_sterilization_run_code?: string | null;
};

export type DataQualityIssue = {
  code: string;
  label: string;
  count: number;
  bag_refs: string[];
};

export type ProductionReportSummary = {
  total_spawn_bags: number;
  total_substrate_bags: number;
  total_contaminated_bags: number;
  contamination_rate: number;
  substrate_bags_with_harvest: number;
  substrate_bags_with_dry_weight: number;
  total_harvest_kg: number;
  total_dry_weight_kg: number;
  overall_bio_efficiency?: number | null;
};

export type ProductionReport = {
  generated_at: string;
  summary: ProductionReportSummary;
  contamination_by_bag_type: ReportGroup[];
  contamination_by_species: ReportGroup[];
  contamination_by_liquid_culture: ReportGroup[];
  contamination_by_inoculation_source_type: ReportGroup[];
  contamination_by_spawn_generation: ReportGroup[];
  contamination_by_source_sterilization_run: ReportGroup[];
  contamination_by_pasteurization_run: ReportGroup[];
  contamination_by_parent_spawn_bag: ReportGroup[];
  contaminated_bags: ContaminationCase[];
  data_quality_issues: DataQualityIssue[];
  pasteurization_runs: PasteurizationRunMetrics[];
  substrate_bags: SubstrateBagMetrics[];
};

export type SterilizationRunDetail = SterilizationRun & {
  bags: Bag[];
  summary: BagCollectionSummary;
  downstream_substrate_bags: SubstrateBagMetrics[];
  downstream_summary: BagCollectionSummary;
};

export type PasteurizationRunDetail = PasteurizationRun & {
  bags: SubstrateBagMetrics[];
  summary: BagCollectionSummary;
};
