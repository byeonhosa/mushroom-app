-- Upgrade spawn tracking and batch inoculation schema to batch-level attribution.
-- This migration is idempotent and can run against databases initialized from 001.

CREATE TABLE IF NOT EXISTS spawn_batches (
  spawn_batch_id SERIAL PRIMARY KEY,
  spawn_type VARCHAR(40) NOT NULL,
  strain_code VARCHAR(30) NOT NULL,
  vendor VARCHAR(120),
  lot_code VARCHAR(120),
  made_at TIMESTAMPTZ,
  incubation_start_at TIMESTAMPTZ,
  notes TEXT
);

ALTER TABLE spawn_batches
  ADD COLUMN IF NOT EXISTS spawn_type VARCHAR(40),
  ADD COLUMN IF NOT EXISTS strain_code VARCHAR(30),
  ADD COLUMN IF NOT EXISTS vendor VARCHAR(120),
  ADD COLUMN IF NOT EXISTS lot_code VARCHAR(120),
  ADD COLUMN IF NOT EXISTS made_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS incubation_start_at TIMESTAMPTZ;

-- Backfill from legacy columns when present.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'spawn_batches' AND column_name = 'source_type'
  ) THEN
    UPDATE spawn_batches
    SET spawn_type = COALESCE(
      spawn_type,
      CASE
        WHEN source_type = 'IN_HOUSE' THEN 'IN_HOUSE_GRAIN'
        ELSE 'PURCHASED_BLOCK'
      END
    )
    WHERE spawn_type IS NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'spawn_batches' AND column_name = 'name'
  ) THEN
    UPDATE spawn_batches
    SET strain_code = COALESCE(
      strain_code,
      LEFT(
        NULLIF(REGEXP_REPLACE(TRIM(SPLIT_PART(name, '-', 1)), '[^A-Za-z0-9_]', '', 'g'), ''),
        30
      )
    )
    WHERE strain_code IS NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'spawn_batches' AND column_name = 'vendor_lot_code'
  ) THEN
    UPDATE spawn_batches
    SET lot_code = COALESCE(lot_code, vendor_lot_code)
    WHERE lot_code IS NULL;
  END IF;
END $$;

UPDATE spawn_batches
SET spawn_type = 'PURCHASED_BLOCK'
WHERE spawn_type IS NULL;

UPDATE spawn_batches
SET strain_code = 'UNKNOWN'
WHERE strain_code IS NULL OR strain_code = '';

ALTER TABLE spawn_batches
  ALTER COLUMN spawn_type SET NOT NULL,
  ALTER COLUMN strain_code SET NOT NULL;

ALTER TABLE spawn_batches
  DROP COLUMN IF EXISTS source_type,
  DROP COLUMN IF EXISTS name,
  DROP COLUMN IF EXISTS vendor_lot_code;

CREATE TABLE IF NOT EXISTS batch_inoculations (
  batch_inoculation_id SERIAL PRIMARY KEY,
  substrate_batch_id INT NOT NULL REFERENCES substrate_batches(substrate_batch_id) ON DELETE CASCADE,
  spawn_batch_id INT NOT NULL REFERENCES spawn_batches(spawn_batch_id),
  inoculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  spawn_blocks_used INT
);

ALTER TABLE batch_inoculations
  ADD COLUMN IF NOT EXISTS spawn_blocks_used INT;

-- Backfill from legacy units column when present.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'batch_inoculations' AND column_name = 'spawn_units_count'
  ) THEN
    UPDATE batch_inoculations
    SET spawn_blocks_used = COALESCE(spawn_blocks_used, spawn_units_count)
    WHERE spawn_blocks_used IS NULL;
  END IF;
END $$;

-- Keep most recent inoculation for each substrate batch before adding uniqueness.
WITH ranked AS (
  SELECT batch_inoculation_id,
         ROW_NUMBER() OVER (
           PARTITION BY substrate_batch_id
           ORDER BY inoculated_at DESC, batch_inoculation_id DESC
         ) AS rn
  FROM batch_inoculations
)
DELETE FROM batch_inoculations b
USING ranked r
WHERE b.batch_inoculation_id = r.batch_inoculation_id
  AND r.rn > 1;

ALTER TABLE batch_inoculations
  ALTER COLUMN inoculated_at SET NOT NULL;

ALTER TABLE batch_inoculations
  DROP COLUMN IF EXISTS spawn_units_count,
  DROP COLUMN IF EXISTS spawn_used_qty_kg,
  DROP COLUMN IF EXISTS notes;

ALTER TABLE batch_inoculations
  DROP CONSTRAINT IF EXISTS uq_batch_inoculations_substrate_batch_id;

ALTER TABLE batch_inoculations
  ADD CONSTRAINT uq_batch_inoculations_substrate_batch_id UNIQUE (substrate_batch_id);
