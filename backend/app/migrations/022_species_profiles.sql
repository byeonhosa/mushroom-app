-- Species cultivation reference dataset (Crowe-detailed commercial parameters).
-- This is a standalone reference table; it is NOT the operational `mushroom_species`
-- table (which carries FKs from liquid_cultures/bags). Rows are populated from
-- backend/app/seeds/mushroom_species.json via `python -m app.seed_species`.
--
-- `code` holds the JSON `id` (e.g. 'oyster', 'reishi') and is the upsert key.
-- Range fields are stored as nullable *_low / *_high integers; a JSON null means
-- the source gave no clean numeric value and is preserved as SQL NULL (not 0).
-- `pinning_trigger` and `use_type` are effectively enums; allowed values are
-- listed in the JSON _meta.conventions and mirrored in the SpeciesProfile model.

CREATE TABLE IF NOT EXISTS species_profiles (
  species_profile_id            SERIAL PRIMARY KEY,
  code                          VARCHAR(60)  NOT NULL UNIQUE,
  common_name                   VARCHAR(160) NOT NULL,
  scientific_name               VARCHAR(160) NULL,
  difficulty                    VARCHAR(40)  NULL,
  difficulty_rank               INTEGER      NULL,
  use_type                      VARCHAR(20)  NULL,  -- enum: culinary | medicinal | both
  substrate_primary             TEXT         NULL,
  substrate_moisture_pct_low    INTEGER      NULL,
  substrate_moisture_pct_high   INTEGER      NULL,
  spawn_rate_pct_low            INTEGER      NULL,
  spawn_rate_pct_high           INTEGER      NULL,
  incubation_temp_f_low         INTEGER      NULL,
  incubation_temp_f_high        INTEGER      NULL,
  colonization_days_low         INTEGER      NULL,
  colonization_days_high        INTEGER      NULL,
  fruiting_temp_f_low           INTEGER      NULL,
  fruiting_temp_f_high          INTEGER      NULL,
  fruiting_humidity_pct_low     INTEGER      NULL,
  fruiting_humidity_pct_high    INTEGER      NULL,
  fruiting_co2_ppm_low          INTEGER      NULL,
  fruiting_co2_ppm_high         INTEGER      NULL,
  fae_ach_low                   INTEGER      NULL,
  fae_ach_high                  INTEGER      NULL,
  light_lux_low                 INTEGER      NULL,
  light_lux_high                INTEGER      NULL,
  light_hours_per_day_low       INTEGER      NULL,
  light_hours_per_day_high      INTEGER      NULL,
  -- enum: fae_increase | temp_drop | co2_drop | co2_drop_cold_shock
  --       | cold_shock_and_strike | combined | form_dependent
  pinning_trigger               VARCHAR(40)  NULL,
  pin_to_harvest_days_low       INTEGER      NULL,
  pin_to_harvest_days_high      INTEGER      NULL,
  biological_efficiency_pct_low  INTEGER     NULL,
  biological_efficiency_pct_high INTEGER     NULL,
  typical_flushes_low           INTEGER      NULL,
  typical_flushes_high          INTEGER      NULL,
  yield_notes                   TEXT         NULL,
  pricing_notes                 TEXT         NULL,
  notes                         TEXT         NULL
);
