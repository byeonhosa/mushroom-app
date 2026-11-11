-- Reference data that can be switched off, and a culture's parent
-- (SRS REF-3 to REF-7, REF-12, REF-14).
--
-- A recipe, fill profile, grain type or ingredient that has been used cannot
-- be deleted: the runs and lots that used it must keep showing it. It is
-- deactivated instead, which takes it out of the pick lists for new work.
ALTER TABLE spawn_recipes ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE substrate_recipe_versions ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE fill_profiles ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE grain_types ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- The culture this one was made from, so that a contaminated culture can be
-- followed back to its parent.
ALTER TABLE liquid_cultures
  ADD COLUMN IF NOT EXISTS parent_liquid_culture_id INTEGER
    REFERENCES liquid_cultures(liquid_culture_id) ON DELETE SET NULL;
