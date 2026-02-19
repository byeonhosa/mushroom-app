CREATE TABLE IF NOT EXISTS mushroom_species (
  species_id SERIAL PRIMARY KEY,
  code VARCHAR(40) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  latin_name VARCHAR(160) NULL,
  notes TEXT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO mushroom_species (code, name, notes, is_active)
VALUES ('UNKNOWN', 'Unknown Species', 'Default species for legacy/test rows', TRUE)
ON CONFLICT (code) DO NOTHING;

ALTER TABLE blocks
ADD COLUMN IF NOT EXISTS species_id INT NULL;

UPDATE blocks
SET species_id = (
  SELECT species_id FROM mushroom_species WHERE code = 'UNKNOWN'
)
WHERE species_id IS NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_blocks_species_id'
  ) THEN
    ALTER TABLE blocks
      ADD CONSTRAINT fk_blocks_species_id
      FOREIGN KEY (species_id) REFERENCES mushroom_species(species_id);
  END IF;
END $$;

ALTER TABLE blocks
ALTER COLUMN species_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_blocks_species_id ON blocks (species_id);
