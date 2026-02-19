DELETE FROM harvest_events h
USING harvest_events older
WHERE h.harvest_event_id > older.harvest_event_id
  AND h.block_id IS NOT NULL
  AND older.block_id IS NOT NULL
  AND h.block_id = older.block_id
  AND h.flush_number = older.flush_number;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'uq_harvest_events_block_flush'
  ) THEN
    ALTER TABLE harvest_events
      ADD CONSTRAINT uq_harvest_events_block_flush UNIQUE (block_id, flush_number);
  END IF;
END $$;
