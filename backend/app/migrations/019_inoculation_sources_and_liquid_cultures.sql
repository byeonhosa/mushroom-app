CREATE TABLE IF NOT EXISTS liquid_cultures (
    liquid_culture_id SERIAL PRIMARY KEY,
    culture_code VARCHAR(120) NOT NULL UNIQUE,
    species_id INTEGER NOT NULL REFERENCES mushroom_species(species_id),
    source VARCHAR(160),
    prepared_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

ALTER TABLE bags
ADD COLUMN IF NOT EXISTS source_liquid_culture_id INTEGER REFERENCES liquid_cultures(liquid_culture_id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS inoculation_batches (
    inoculation_batch_id SERIAL PRIMARY KEY,
    source_type VARCHAR(20) NOT NULL,
    source_spawn_bag_id VARCHAR(80) REFERENCES bags(bag_id) ON DELETE SET NULL,
    source_liquid_culture_id INTEGER REFERENCES liquid_cultures(liquid_culture_id) ON DELETE SET NULL,
    species_id INTEGER REFERENCES mushroom_species(species_id) ON DELETE SET NULL,
    inoculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS inoculation_batch_targets (
    inoculation_batch_target_id SERIAL PRIMARY KEY,
    inoculation_batch_id INTEGER NOT NULL REFERENCES inoculation_batches(inoculation_batch_id) ON DELETE CASCADE,
    bag_id VARCHAR(80) NOT NULL REFERENCES bags(bag_id) ON DELETE CASCADE,
    CONSTRAINT uq_inoculation_batch_targets_bag UNIQUE (bag_id)
);

CREATE INDEX IF NOT EXISTS ix_bags_source_liquid_culture_id
ON bags (source_liquid_culture_id);

CREATE INDEX IF NOT EXISTS ix_inoculation_batches_source_spawn_bag_id
ON inoculation_batches (source_spawn_bag_id);

CREATE INDEX IF NOT EXISTS ix_inoculation_batches_source_liquid_culture_id
ON inoculation_batches (source_liquid_culture_id);

CREATE INDEX IF NOT EXISTS ix_inoculation_batch_targets_batch_id
ON inoculation_batch_targets (inoculation_batch_id);
