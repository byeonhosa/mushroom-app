ALTER TABLE bags
ALTER COLUMN species_id DROP NOT NULL;

ALTER TABLE bags
ADD COLUMN IF NOT EXISTS bag_code VARCHAR(120);

ALTER TABLE bags
ADD COLUMN IF NOT EXISTS labeled_at TIMESTAMPTZ;

UPDATE bags
SET bag_code = bag_id,
    labeled_at = COALESCE(labeled_at, inoculated_at, created_at)
WHERE bag_code IS NULL
  AND inoculated_at IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_bags_bag_code
ON bags (bag_code)
WHERE bag_code IS NOT NULL;
