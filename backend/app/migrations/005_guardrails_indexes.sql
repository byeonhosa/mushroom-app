-- Add DB guardrails and lookup indexes for spawn tracking.
-- Idempotent: constraint creation is guarded, indexes use IF NOT EXISTS.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ck_spawn_batches_spawn_type_allowed'
  ) THEN
    ALTER TABLE spawn_batches
      ADD CONSTRAINT ck_spawn_batches_spawn_type_allowed
      CHECK (spawn_type IN ('PURCHASED_BLOCK', 'IN_HOUSE_GRAIN'));
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'ck_batch_inoculations_spawn_blocks_used_nonnegative'
  ) THEN
    ALTER TABLE batch_inoculations
      ADD CONSTRAINT ck_batch_inoculations_spawn_blocks_used_nonnegative
      CHECK (spawn_blocks_used IS NULL OR spawn_blocks_used >= 0);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_batch_inoculations_spawn_batch_id
  ON batch_inoculations (spawn_batch_id);

CREATE INDEX IF NOT EXISTS idx_spawn_batches_strain_code
  ON spawn_batches (strain_code);
