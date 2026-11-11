-- Counters for internal bag IDs (SRS BAG-11).
--
-- SPNREC-0001 and SUBREC-0001 numbers used to be chosen by reading the
-- highest number in the bags table, so two requests at the same moment could
-- pick the same one. Each family now has a counter row that the application
-- increments inside the transaction that creates the bags; the row lock
-- makes concurrent requests take their numbers in turn.
CREATE TABLE IF NOT EXISTS id_counters (
  name VARCHAR(40) PRIMARY KEY,
  next_value INTEGER NOT NULL DEFAULT 1 CHECK (next_value >= 1)
);

INSERT INTO id_counters (name, next_value)
SELECT prefix,
       COALESCE(
         (SELECT MAX(CAST(SUBSTRING(bag_id FROM '^' || prefix || '-([0-9]+)$') AS INTEGER))
            FROM bags
           WHERE bag_id ~ ('^' || prefix || '-[0-9]+$')),
         0
       ) + 1
FROM (VALUES ('SPNREC'), ('SUBREC')) AS families(prefix)
ON CONFLICT (name) DO NOTHING;
