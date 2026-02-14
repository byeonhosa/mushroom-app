CREATE TABLE IF NOT EXISTS zones (
  zone_id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  zone_type VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS fill_profiles (
  fill_profile_id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  target_dry_kg_per_bag NUMERIC(10,3) NOT NULL,
  target_water_kg_per_bag NUMERIC(10,3) NOT NULL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS substrate_recipe_versions (
  substrate_recipe_version_id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS thermal_runs (
  thermal_run_id SERIAL PRIMARY KEY,
  process_type VARCHAR(40) NOT NULL,
  unloaded_at TIMESTAMPTZ NOT NULL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS spawn_batches (
  spawn_batch_id SERIAL PRIMARY KEY,
  source_type VARCHAR(20) NOT NULL,
  name VARCHAR(120) NOT NULL,
  vendor_lot_code VARCHAR(120),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS substrate_batches (
  substrate_batch_id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  substrate_recipe_version_id INT NOT NULL REFERENCES substrate_recipe_versions(substrate_recipe_version_id),
  fill_profile_id INT NOT NULL REFERENCES fill_profiles(fill_profile_id),
  bag_count INT NOT NULL,
  mixed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  mix_zone_id INT REFERENCES zones(zone_id),
  incubation_zone_id INT REFERENCES zones(zone_id),
  incubation_start_at TIMESTAMPTZ,
  fruiting_zone_id INT REFERENCES zones(zone_id),
  thermal_run_id INT REFERENCES thermal_runs(thermal_run_id),
  sample_moisture_wb_pct NUMERIC(6,3),
  sample_wet_weight_kg NUMERIC(10,3),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS substrate_bags (
  bag_id VARCHAR(64) PRIMARY KEY,
  substrate_batch_id INT NOT NULL REFERENCES substrate_batches(substrate_batch_id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  status VARCHAR(40) NOT NULL DEFAULT 'INCUBATING'
);

CREATE TABLE IF NOT EXISTS batch_inoculations (
  batch_inoculation_id SERIAL PRIMARY KEY,
  substrate_batch_id INT NOT NULL REFERENCES substrate_batches(substrate_batch_id) ON DELETE CASCADE,
  spawn_batch_id INT NOT NULL REFERENCES spawn_batches(spawn_batch_id),
  inoculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  spawn_units_count INT,
  spawn_used_qty_kg NUMERIC(10,3),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS harvest_events (
  harvest_event_id SERIAL PRIMARY KEY,
  bag_id VARCHAR(64) NOT NULL REFERENCES substrate_bags(bag_id) ON DELETE CASCADE,
  harvested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  flush_number INT NOT NULL,
  fresh_weight_kg NUMERIC(10,3) NOT NULL,
  notes TEXT,
  CONSTRAINT ck_flush_number_1_2 CHECK (flush_number IN (1,2))
);
