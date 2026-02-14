INSERT INTO zones(name, zone_type)
VALUES
  ('Mixing Area', 'MIXING'),
  ('Incubation Tent 1', 'INCUBATION'),
  ('Fruiting Tent 1', 'FRUITING')
ON CONFLICT DO NOTHING;

INSERT INTO fill_profiles(name, target_dry_kg_per_bag, target_water_kg_per_bag, notes)
VALUES ('Standard 1.00kg dry + 1.25kg water', 1.000, 1.250, 'Current hand-fill standard')
ON CONFLICT DO NOTHING;

INSERT INTO substrate_recipe_versions(name, notes)
VALUES ('Default Substrate Recipe v1', 'Set items in Phase 3 once ingredient lots are tracked')
ON CONFLICT DO NOTHING;
