-- Ingredients, ingredient lots, and per-batch add-ins.

CREATE TABLE IF NOT EXISTS ingredients (
  ingredient_id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  category VARCHAR(120),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS ingredient_lots (
  ingredient_lot_id SERIAL PRIMARY KEY,
  ingredient_id INT NOT NULL REFERENCES ingredients(ingredient_id),
  vendor VARCHAR(120),
  lot_code VARCHAR(120),
  received_at TIMESTAMPTZ,
  unit_cost_per_kg NUMERIC(12,4),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS substrate_batch_addins (
  substrate_batch_addin_id SERIAL PRIMARY KEY,
  substrate_batch_id INT NOT NULL REFERENCES substrate_batches(substrate_batch_id) ON DELETE CASCADE,
  ingredient_lot_id INT NOT NULL REFERENCES ingredient_lots(ingredient_lot_id),
  dry_kg NUMERIC(12,4),
  pct_of_base_dry NUMERIC(8,4),
  notes TEXT
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_substrate_batch_addins_dry_kg_nonnegative'
  ) THEN
    ALTER TABLE substrate_batch_addins
      ADD CONSTRAINT ck_substrate_batch_addins_dry_kg_nonnegative
      CHECK (dry_kg IS NULL OR dry_kg >= 0);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_substrate_batch_addins_pct_nonnegative'
  ) THEN
    ALTER TABLE substrate_batch_addins
      ADD CONSTRAINT ck_substrate_batch_addins_pct_nonnegative
      CHECK (pct_of_base_dry IS NULL OR pct_of_base_dry >= 0);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'ck_substrate_batch_addins_dry_or_pct_required'
  ) THEN
    ALTER TABLE substrate_batch_addins
      ADD CONSTRAINT ck_substrate_batch_addins_dry_or_pct_required
      CHECK (dry_kg IS NOT NULL OR pct_of_base_dry IS NOT NULL);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_substrate_batch_addins_substrate_batch_id
  ON substrate_batch_addins (substrate_batch_id);

CREATE INDEX IF NOT EXISTS idx_substrate_batch_addins_ingredient_lot_id
  ON substrate_batch_addins (ingredient_lot_id);
