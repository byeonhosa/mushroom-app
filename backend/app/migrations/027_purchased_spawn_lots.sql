-- Purchased spawn lots as an inoculation source (SRS REF-11, INO-6, INO-7).
--
-- The farm inoculates its substrate from grain spawn bought from a supplier.
-- Until now the only sources the app knew were a liquid culture and one of
-- the farm's own spawn bags. A purchased lot is recorded once and can then
-- inoculate any number of sessions, of substrate or of spawn bags, until
-- someone marks it used up. Bags and inoculation sessions point back to it.
CREATE TABLE IF NOT EXISTS purchased_spawn_lots (
  purchased_spawn_lot_id SERIAL PRIMARY KEY,
  lot_code VARCHAR(40) NOT NULL UNIQUE,
  vendor VARCHAR(160) NOT NULL,
  vendor_lot_number VARCHAR(120),
  species_id INTEGER NOT NULL REFERENCES mushroom_species(species_id),
  grain_type_id INTEGER REFERENCES grain_types(grain_type_id) ON DELETE SET NULL,
  received_at TIMESTAMPTZ NOT NULL,
  quantity NUMERIC(10, 2) CHECK (quantity IS NULL OR quantity > 0),
  quantity_unit VARCHAR(20),
  notes TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  used_up_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_purchased_spawn_lots_species ON purchased_spawn_lots(species_id);

ALTER TABLE bags
  ADD COLUMN IF NOT EXISTS source_purchased_spawn_lot_id INTEGER
    REFERENCES purchased_spawn_lots(purchased_spawn_lot_id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_bags_source_purchased_spawn_lot ON bags(source_purchased_spawn_lot_id);

ALTER TABLE inoculation_batches
  ADD COLUMN IF NOT EXISTS source_purchased_spawn_lot_id INTEGER
    REFERENCES purchased_spawn_lots(purchased_spawn_lot_id) ON DELETE SET NULL;
