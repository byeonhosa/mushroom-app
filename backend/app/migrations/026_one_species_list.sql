-- One species list (SRS REF-1, REF-2, SPR-2; brief section 10).
--
-- mushroom_species gains the identifier shared with the farm website (slug)
-- and the fields the website will read: availability_tier, sale_path,
-- in_rotation_now, restrictions. Their values follow the website's own
-- vocabulary; a species is 'hidden' until an administrator says otherwise.
--
-- species_profiles becomes the cultivation profile OF a species: one row per
-- species, linked by species_id, with a note of whether its values come from
-- the farm's sources or from outside research. The eight rows it held were
-- keyed by codes of their own (lions_mane, king_oyster, ...) with no link to
-- the species list. They are reference data seeded from the repository at
-- every start, so they are cleared here and reseeded, linked, by
-- app.seed_species.
ALTER TABLE mushroom_species
  ADD COLUMN IF NOT EXISTS slug VARCHAR(60),
  ADD COLUMN IF NOT EXISTS availability_tier VARCHAR(40),
  ADD COLUMN IF NOT EXISTS sale_path VARCHAR(40) NOT NULL DEFAULT 'hidden',
  ADD COLUMN IF NOT EXISTS in_rotation_now BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS restrictions TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mushroom_species_slug ON mushroom_species(slug);

ALTER TABLE mushroom_species
  ADD CONSTRAINT ck_mushroom_species_availability_tier CHECK (
    availability_tier IS NULL OR availability_tier IN (
      'year-round', 'in-rotation-now', 'returning', 'wholesale-only', 'functional-coming-later'
    )
  ),
  ADD CONSTRAINT ck_mushroom_species_sale_path CHECK (
    sale_path IN (
      'available', 'low-stock', 'sold-out', 'coming-soon', 'seasonal',
      'preorder', 'hidden', 'wholesale-only', 'inquiry-only'
    )
  );

DELETE FROM species_profiles;

ALTER TABLE species_profiles
  ADD COLUMN IF NOT EXISTS species_id INTEGER NOT NULL
    REFERENCES mushroom_species(species_id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS data_source VARCHAR(20) NOT NULL DEFAULT 'farm'
    CHECK (data_source IN ('farm', 'researched')),
  ADD COLUMN IF NOT EXISTS source_note TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_species_profiles_species ON species_profiles(species_id);
