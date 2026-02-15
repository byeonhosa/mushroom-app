-- Add in-house grain spawn detail fields to spawn_batches.
-- Idempotent where possible.

ALTER TABLE spawn_batches
  ADD COLUMN IF NOT EXISTS grain_dry_kg NUMERIC(10,3),
  ADD COLUMN IF NOT EXISTS grain_water_kg NUMERIC(10,3),
  ADD COLUMN IF NOT EXISTS supplement_kg NUMERIC(10,3),
  ADD COLUMN IF NOT EXISTS lc_vendor VARCHAR(120),
  ADD COLUMN IF NOT EXISTS lc_code VARCHAR(120),
  ADD COLUMN IF NOT EXISTS sterilization_run_code VARCHAR(120),
  ADD COLUMN IF NOT EXISTS incubation_zone_id INT REFERENCES zones(zone_id);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ck_spawn_batches_grain_dry_kg_nonnegative'
  ) THEN
    ALTER TABLE spawn_batches
      ADD CONSTRAINT ck_spawn_batches_grain_dry_kg_nonnegative
      CHECK (grain_dry_kg IS NULL OR grain_dry_kg >= 0);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ck_spawn_batches_grain_water_kg_nonnegative'
  ) THEN
    ALTER TABLE spawn_batches
      ADD CONSTRAINT ck_spawn_batches_grain_water_kg_nonnegative
      CHECK (grain_water_kg IS NULL OR grain_water_kg >= 0);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ck_spawn_batches_supplement_kg_nonnegative'
  ) THEN
    ALTER TABLE spawn_batches
      ADD CONSTRAINT ck_spawn_batches_supplement_kg_nonnegative
      CHECK (supplement_kg IS NULL OR supplement_kg >= 0);
  END IF;
END $$;
