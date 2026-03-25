ALTER TABLE bags
ADD COLUMN IF NOT EXISTS target_dry_kg NUMERIC(10,3);

ALTER TABLE bags
ADD COLUMN IF NOT EXISTS actual_dry_kg NUMERIC(10,3);

UPDATE bags AS b
SET target_dry_kg = fp.target_dry_kg_per_bag
FROM mix_lots AS ml
JOIN fill_profiles AS fp ON fp.fill_profile_id = ml.fill_profile_id
WHERE b.bag_type = 'SUBSTRATE'
  AND b.mix_lot_id = ml.mix_lot_id
  AND b.target_dry_kg IS NULL;
