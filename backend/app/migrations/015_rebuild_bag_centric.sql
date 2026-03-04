-- Full schema rebuild: bag-centric production model
-- Drops all previous tables and creates new schema

-- Drop existing tables (dependents first)
DROP TABLE IF EXISTS harvest_events CASCADE;
DROP TABLE IF EXISTS inoculations CASCADE;
DROP TABLE IF EXISTS substrate_batch_addins CASCADE;
DROP TABLE IF EXISTS substrate_bags CASCADE;
DROP TABLE IF EXISTS batch_inoculations CASCADE;
DROP TABLE IF EXISTS blocks CASCADE;
DROP TABLE IF EXISTS substrate_batches CASCADE;
DROP TABLE IF EXISTS ingredient_lots CASCADE;
DROP TABLE IF EXISTS pasteurization_runs CASCADE;
DROP TABLE IF EXISTS sterilization_runs CASCADE;
DROP TABLE IF EXISTS spawn_batches CASCADE;
DROP TABLE IF EXISTS ingredients CASCADE;
DROP TABLE IF EXISTS mix_lots CASCADE;
DROP TABLE IF EXISTS fill_profiles CASCADE;
DROP TABLE IF EXISTS substrate_recipe_versions CASCADE;
DROP TABLE IF EXISTS spawn_recipes CASCADE;
DROP TABLE IF EXISTS grain_types CASCADE;
DROP TABLE IF EXISTS mushroom_species CASCADE;
DROP TABLE IF EXISTS thermal_runs CASCADE;
DROP TABLE IF EXISTS zones CASCADE;

-- Reference: zones
CREATE TABLE zones (
  zone_id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  zone_type VARCHAR(20) NOT NULL
);

-- Reference: substrate_recipe_versions (Masters Mix, etc.)
CREATE TABLE substrate_recipe_versions (
  substrate_recipe_version_id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  recipe_code VARCHAR(20) NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes TEXT
);

-- Reference: spawn_recipes (grain spawn recipe)
CREATE TABLE spawn_recipes (
  spawn_recipe_id SERIAL PRIMARY KEY,
  recipe_code VARCHAR(40) NOT NULL UNIQUE,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Reference: fill_profiles
CREATE TABLE fill_profiles (
  fill_profile_id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  target_dry_kg_per_bag NUMERIC(10,3) NOT NULL,
  target_water_kg_per_bag NUMERIC(10,3) NOT NULL,
  notes TEXT
);

-- Reference: mix_lots (single substrate mix event; can feed multiple pasteurization runs)
CREATE TABLE mix_lots (
  mix_lot_id SERIAL PRIMARY KEY,
  lot_code VARCHAR(120) NOT NULL UNIQUE,
  substrate_recipe_version_id INT NOT NULL REFERENCES substrate_recipe_versions(substrate_recipe_version_id),
  fill_profile_id INT NOT NULL REFERENCES fill_profiles(fill_profile_id),
  mixed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes TEXT
);

-- Reference: ingredients, ingredient_lots
CREATE TABLE ingredients (
  ingredient_id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  category VARCHAR(120),
  notes TEXT
);

CREATE TABLE ingredient_lots (
  ingredient_lot_id SERIAL PRIMARY KEY,
  ingredient_id INT NOT NULL REFERENCES ingredients(ingredient_id),
  vendor VARCHAR(120),
  lot_code VARCHAR(120),
  received_at TIMESTAMPTZ,
  unit_cost_per_kg NUMERIC(12,4),
  notes TEXT
);

-- Mix lot addins (ingredients added to a mix for testing)
CREATE TABLE mix_lot_addins (
  mix_lot_addin_id SERIAL PRIMARY KEY,
  mix_lot_id INT NOT NULL REFERENCES mix_lots(mix_lot_id) ON DELETE CASCADE,
  ingredient_lot_id INT NOT NULL REFERENCES ingredient_lots(ingredient_lot_id),
  dry_kg NUMERIC(12,4),
  pct_of_base_dry NUMERIC(8,4),
  notes TEXT
);

-- Reference: grain_types
CREATE TABLE grain_types (
  grain_type_id SERIAL PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE,
  notes TEXT
);

-- Reference: mushroom_species
CREATE TABLE mushroom_species (
  species_id SERIAL PRIMARY KEY,
  code VARCHAR(40) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  latin_name VARCHAR(160),
  notes TEXT,
  is_active BOOLEAN NOT NULL DEFAULT true
);

-- Pasteurization runs (thermal batch for substrate bags)
CREATE TABLE pasteurization_runs (
  pasteurization_run_id SERIAL PRIMARY KEY,
  run_code VARCHAR(120) NOT NULL UNIQUE,
  mix_lot_id INT NOT NULL REFERENCES mix_lots(mix_lot_id),
  substrate_recipe_version_id INT NOT NULL REFERENCES substrate_recipe_versions(substrate_recipe_version_id),
  steam_start_at TIMESTAMPTZ,
  steam_end_at TIMESTAMPTZ,
  unloaded_at TIMESTAMPTZ NOT NULL,
  bag_count INT NOT NULL,
  notes TEXT
);

-- Sterilization runs (thermal batch for spawn bags)
CREATE TABLE sterilization_runs (
  sterilization_run_id SERIAL PRIMARY KEY,
  run_code VARCHAR(120) NOT NULL UNIQUE,
  spawn_recipe_id INT NOT NULL REFERENCES spawn_recipes(spawn_recipe_id),
  grain_type_id INT NOT NULL REFERENCES grain_types(grain_type_id),
  cycle_start_at TIMESTAMPTZ,
  cycle_end_at TIMESTAMPTZ,
  unloaded_at TIMESTAMPTZ NOT NULL,
  bag_count INT NOT NULL,
  temp_c NUMERIC(6,2),
  psi NUMERIC(6,2),
  hold_minutes INT,
  notes TEXT
);

-- Bags: unified table for spawn and substrate
CREATE TABLE bags (
  bag_id VARCHAR(80) PRIMARY KEY,
  bag_type VARCHAR(20) NOT NULL CHECK (bag_type IN ('SPAWN', 'SUBSTRATE')),
  species_id INT NOT NULL REFERENCES mushroom_species(species_id),
  pasteurization_run_id INT REFERENCES pasteurization_runs(pasteurization_run_id) ON DELETE SET NULL,
  sterilization_run_id INT REFERENCES sterilization_runs(sterilization_run_id) ON DELETE SET NULL,
  mix_lot_id INT REFERENCES mix_lots(mix_lot_id) ON DELETE SET NULL,
  substrate_recipe_version_id INT REFERENCES substrate_recipe_versions(substrate_recipe_version_id) ON DELETE SET NULL,
  spawn_recipe_id INT REFERENCES spawn_recipes(spawn_recipe_id) ON DELETE SET NULL,
  grain_type_id INT REFERENCES grain_types(grain_type_id) ON DELETE SET NULL,
  parent_spawn_bag_id VARCHAR(80) REFERENCES bags(bag_id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  inoculated_at TIMESTAMPTZ,
  incubation_start_at TIMESTAMPTZ,
  fruiting_start_at TIMESTAMPTZ,
  disposed_at TIMESTAMPTZ,
  disposal_reason VARCHAR(20) CHECK (disposal_reason IN ('CONTAMINATION', 'FINAL_HARVEST')),
  consumed_at TIMESTAMPTZ,
  status VARCHAR(40) NOT NULL DEFAULT 'FILLED',
  notes TEXT,
  CONSTRAINT ck_bag_thermal_run CHECK (
    (bag_type = 'SPAWN' AND sterilization_run_id IS NOT NULL AND pasteurization_run_id IS NULL)
    OR
    (bag_type = 'SUBSTRATE' AND (pasteurization_run_id IS NOT NULL OR sterilization_run_id IS NOT NULL))
  )
);

CREATE INDEX idx_bags_bag_type ON bags(bag_type);
CREATE INDEX idx_bags_species_id ON bags(species_id);
CREATE INDEX idx_bags_pasteurization_run_id ON bags(pasteurization_run_id);
CREATE INDEX idx_bags_sterilization_run_id ON bags(sterilization_run_id);
CREATE INDEX idx_bags_status ON bags(status);
CREATE INDEX idx_bags_parent_spawn_bag_id ON bags(parent_spawn_bag_id);

-- Inoculations (per-bag: which spawn bag inoculated which substrate bag)
CREATE TABLE inoculations (
  inoculation_id SERIAL PRIMARY KEY,
  substrate_bag_id VARCHAR(80) NOT NULL UNIQUE REFERENCES bags(bag_id) ON DELETE CASCADE,
  spawn_bag_id VARCHAR(80) NOT NULL REFERENCES bags(bag_id) ON DELETE RESTRICT,
  inoculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes TEXT
);

CREATE INDEX idx_inoculations_spawn_bag_id ON inoculations(spawn_bag_id);

-- Harvest events (substrate bags only, flush 1 or 2)
CREATE TABLE harvest_events (
  harvest_event_id SERIAL PRIMARY KEY,
  bag_id VARCHAR(80) NOT NULL REFERENCES bags(bag_id) ON DELETE CASCADE,
  flush_number INT NOT NULL CHECK (flush_number IN (1, 2)),
  fresh_weight_kg NUMERIC(10,3) NOT NULL CHECK (fresh_weight_kg > 0),
  harvested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes TEXT,
  CONSTRAINT uq_harvest_events_bag_flush UNIQUE (bag_id, flush_number)
);

CREATE INDEX idx_harvest_events_bag_id ON harvest_events(bag_id);

-- Seed defaults
INSERT INTO zones(name, zone_type) VALUES
  ('Mixing Area', 'MIXING'),
  ('Incubation Tent 1', 'INCUBATION'),
  ('Fruiting Tent 1', 'FRUITING'),
  ('Grow Tent 1', 'FRUITING')
ON CONFLICT (name) DO NOTHING;

INSERT INTO fill_profiles(name, target_dry_kg_per_bag, target_water_kg_per_bag, notes)
VALUES ('Standard 1.00kg dry + 1.25kg water', 1.000, 1.250, 'Current hand-fill standard')
ON CONFLICT (name) DO NOTHING;

INSERT INTO substrate_recipe_versions(name, recipe_code, notes)
VALUES ('Masters Mix v1', 'MM', '50/50 hardwood pellets + soyhull pellets')
ON CONFLICT (recipe_code) DO NOTHING;

INSERT INTO spawn_recipes(recipe_code, notes)
VALUES ('SR1', 'Default grain spawn recipe')
ON CONFLICT (recipe_code) DO NOTHING;

INSERT INTO grain_types(name, notes)
VALUES ('Rye', 'Default grain type')
ON CONFLICT (name) DO NOTHING;

INSERT INTO mushroom_species(code, name, latin_name, is_active)
VALUES ('LM', 'Lion''s Mane', 'Hericium erinaceus', true)
ON CONFLICT (code) DO NOTHING;

INSERT INTO mix_lots(lot_code, substrate_recipe_version_id, fill_profile_id)
SELECT 'INIT', (SELECT substrate_recipe_version_id FROM substrate_recipe_versions WHERE recipe_code='MM' LIMIT 1),
       (SELECT fill_profile_id FROM fill_profiles LIMIT 1)
WHERE NOT EXISTS (SELECT 1 FROM mix_lots WHERE lot_code='INIT');
