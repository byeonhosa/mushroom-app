-- Block-based harvest canonical fields while keeping legacy columns.

ALTER TABLE harvest_events
  ADD COLUMN IF NOT EXISTS block_id INT REFERENCES blocks(block_id);

ALTER TABLE harvest_events
  ADD COLUMN IF NOT EXISTS flush_number INT;

ALTER TABLE harvest_events
  ADD COLUMN IF NOT EXISTS fresh_weight_kg NUMERIC(10,3);

ALTER TABLE harvest_events
  ADD COLUMN IF NOT EXISTS harvested_at TIMESTAMPTZ;

ALTER TABLE harvest_events
  ADD COLUMN IF NOT EXISTS notes TEXT;

ALTER TABLE harvest_events
  ALTER COLUMN bag_id DROP NOT NULL;

UPDATE harvest_events
SET harvested_at = now()
WHERE harvested_at IS NULL;

ALTER TABLE harvest_events
  ALTER COLUMN harvested_at SET DEFAULT now();

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ck_harvest_events_flush_1_2'
  ) THEN
    ALTER TABLE harvest_events
      ADD CONSTRAINT ck_harvest_events_flush_1_2
      CHECK (flush_number IN (1,2));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ck_harvest_events_fresh_weight_positive'
  ) THEN
    ALTER TABLE harvest_events
      ADD CONSTRAINT ck_harvest_events_fresh_weight_positive
      CHECK (fresh_weight_kg > 0);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_harvest_events_block_id
  ON harvest_events (block_id);
