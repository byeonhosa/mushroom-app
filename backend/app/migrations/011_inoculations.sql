-- Block-level inoculation attribution.

CREATE TABLE IF NOT EXISTS inoculations (
  inoculation_id SERIAL PRIMARY KEY,
  child_block_id INT NOT NULL REFERENCES blocks(block_id) ON DELETE CASCADE,
  parent_spawn_block_id INT NOT NULL REFERENCES blocks(block_id) ON DELETE RESTRICT,
  inoculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes TEXT NULL,
  CONSTRAINT uq_inoculations_child_block_id UNIQUE (child_block_id)
);

CREATE INDEX IF NOT EXISTS idx_inoculations_parent_spawn_block_id
  ON inoculations (parent_spawn_block_id);

CREATE INDEX IF NOT EXISTS idx_inoculations_child_block_id
  ON inoculations (child_block_id);
