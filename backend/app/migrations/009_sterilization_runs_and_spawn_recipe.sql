-- Autoclave sterilization runs + in-house spawn recipe by weight.

CREATE TABLE IF NOT EXISTS sterilization_runs (
  sterilization_run_id SERIAL PRIMARY KEY,
  run_code VARCHAR(120) NOT NULL UNIQUE,
  cycle_start_at TIMESTAMPTZ,
  cycle_end_at TIMESTAMPTZ,
  unloaded_at TIMESTAMPTZ NOT NULL,
  temp_c NUMERIC(6,2),
  psi NUMERIC(6,2),
  hold_minutes INT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS grain_types (
  grain_type_id SERIAL PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE,
  notes TEXT
);

INSERT INTO grain_types (name, notes)
VALUES ('Rye', 'Default grain type seed')
ON CONFLICT (name) DO NOTHING;

ALTER TABLE spawn_batches
  ADD COLUMN IF NOT EXISTS sterilization_run_id INT REFERENCES sterilization_runs(sterilization_run_id),
  ADD COLUMN IF NOT EXISTS grain_type_id INT REFERENCES grain_types(grain_type_id),
  ADD COLUMN IF NOT EXISTS grain_kg NUMERIC(10,3),
  ADD COLUMN IF NOT EXISTS vermiculite_kg NUMERIC(10,3),
  ADD COLUMN IF NOT EXISTS water_kg NUMERIC(10,3),
  ADD COLUMN IF NOT EXISTS supplement_kg NUMERIC(10,3);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_spawn_batches_grain_kg_nonnegative'
  ) THEN
    ALTER TABLE spawn_batches
      ADD CONSTRAINT ck_spawn_batches_grain_kg_nonnegative
      CHECK (grain_kg IS NULL OR grain_kg >= 0);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_spawn_batches_vermiculite_kg_nonnegative'
  ) THEN
    ALTER TABLE spawn_batches
      ADD CONSTRAINT ck_spawn_batches_vermiculite_kg_nonnegative
      CHECK (vermiculite_kg IS NULL OR vermiculite_kg >= 0);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_spawn_batches_water_kg_nonnegative'
  ) THEN
    ALTER TABLE spawn_batches
      ADD CONSTRAINT ck_spawn_batches_water_kg_nonnegative
      CHECK (water_kg IS NULL OR water_kg >= 0);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_spawn_batches_supplement_kg_nonnegative'
  ) THEN
    ALTER TABLE spawn_batches
      ADD CONSTRAINT ck_spawn_batches_supplement_kg_nonnegative
      CHECK (supplement_kg IS NULL OR supplement_kg >= 0);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_spawn_batches_sterilization_run_id
  ON spawn_batches (sterilization_run_id);

CREATE INDEX IF NOT EXISTS idx_spawn_batches_grain_type_id
  ON spawn_batches (grain_type_id);
