-- Relax legacy strict check constraints for in-house-only spawn fields.
-- Purchased spawn batches must allow these fields to remain NULL.

DO $$
DECLARE
  c RECORD;
  def TEXT;
BEGIN
  FOR c IN
    SELECT con.oid, con.conname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'spawn_batches'
      AND con.contype = 'c'
  LOOP
    def := pg_get_constraintdef(c.oid);

    IF (
      (def ILIKE '%spawn_type%' AND def ILIKE '%PURCHASED_BLOCK%')
      OR def ILIKE '%grain_dry_kg IS NOT NULL%'
      OR def ILIKE '%grain_water_kg IS NOT NULL%'
      OR def ILIKE '%supplement_kg IS NOT NULL%'
      OR def ILIKE '%lc_vendor IS NOT NULL%'
      OR def ILIKE '%lc_code IS NOT NULL%'
      OR def ILIKE '%sterilization_run_code IS NOT NULL%'
      OR def ILIKE '%incubation_zone_id IS NOT NULL%'
    )
    AND c.conname NOT IN (
      'ck_spawn_batches_grain_dry_kg_nonnegative',
      'ck_spawn_batches_grain_water_kg_nonnegative',
      'ck_spawn_batches_supplement_kg_nonnegative'
    ) THEN
      EXECUTE format('ALTER TABLE spawn_batches DROP CONSTRAINT IF EXISTS %I', c.conname);
    END IF;
  END LOOP;
END $$;
