CREATE TABLE IF NOT EXISTS pasteurization_runs (
  pasteurization_run_id SERIAL PRIMARY KEY,
  run_code VARCHAR(120) NOT NULL UNIQUE,
  steam_start_at TIMESTAMPTZ,
  steam_end_at TIMESTAMPTZ,
  unloaded_at TIMESTAMPTZ NOT NULL,
  notes TEXT
);

ALTER TABLE substrate_batches
  ADD COLUMN IF NOT EXISTS pasteurization_run_id INT REFERENCES pasteurization_runs(pasteurization_run_id);
