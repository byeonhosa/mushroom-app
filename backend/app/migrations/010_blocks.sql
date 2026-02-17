-- Block-first slice: blocks table + minimal lookup tables required for references.

CREATE TABLE IF NOT EXISTS mix_lots (
  mix_lot_id SERIAL PRIMARY KEY,
  lot_code VARCHAR(120) NOT NULL UNIQUE,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS spawn_recipes (
  spawn_recipe_id SERIAL PRIMARY KEY,
  recipe_code VARCHAR(120) NOT NULL UNIQUE,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS blocks (
  block_id SERIAL PRIMARY KEY,
  block_code VARCHAR(120) NOT NULL UNIQUE,
  block_type VARCHAR(20) NOT NULL CHECK (block_type IN ('SPAWN','SUBSTRATE')),

  mix_lot_id INT NULL REFERENCES mix_lots(mix_lot_id) ON DELETE SET NULL,
  pasteurization_run_id INT NULL REFERENCES pasteurization_runs(pasteurization_run_id) ON DELETE SET NULL,
  sterilization_run_id INT NULL REFERENCES sterilization_runs(sterilization_run_id) ON DELETE SET NULL,
  spawn_recipe_id INT NULL REFERENCES spawn_recipes(spawn_recipe_id) ON DELETE SET NULL,

  substrate_batch_id INT NULL REFERENCES substrate_batches(substrate_batch_id) ON DELETE SET NULL,
  spawn_batch_id INT NULL REFERENCES spawn_batches(spawn_batch_id) ON DELETE SET NULL,

  status VARCHAR(30) NULL,
  notes TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_blocks_mix_lot_id ON blocks (mix_lot_id);
CREATE INDEX IF NOT EXISTS idx_blocks_pasteurization_run_id ON blocks (pasteurization_run_id);
CREATE INDEX IF NOT EXISTS idx_blocks_sterilization_run_id ON blocks (sterilization_run_id);
CREATE INDEX IF NOT EXISTS idx_blocks_spawn_recipe_id ON blocks (spawn_recipe_id);
CREATE INDEX IF NOT EXISTS idx_blocks_substrate_batch_id ON blocks (substrate_batch_id);
CREATE INDEX IF NOT EXISTS idx_blocks_spawn_batch_id ON blocks (spawn_batch_id);
CREATE INDEX IF NOT EXISTS idx_blocks_block_type_created_at ON blocks (block_type, created_at);
