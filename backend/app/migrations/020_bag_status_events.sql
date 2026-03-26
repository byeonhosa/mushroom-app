CREATE TABLE IF NOT EXISTS bag_status_events (
    bag_status_event_id SERIAL PRIMARY KEY,
    bag_id VARCHAR(80) NOT NULL REFERENCES bags(bag_id) ON DELETE CASCADE,
    event_type VARCHAR(40) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    detail TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS ix_bag_status_events_bag_id_occurred_at
ON bag_status_events (bag_id, occurred_at, bag_status_event_id);

INSERT INTO bag_status_events (bag_id, event_type, occurred_at, detail)
SELECT
    b.bag_id,
    'CREATED',
    b.created_at,
    CASE
        WHEN b.bag_type = 'SPAWN'
            THEN CONCAT('Spawn bag record created for sterilization run ', COALESCE(sr.run_code, 'unknown'))
        ELSE CONCAT('Substrate bag record created for pasteurization run ', COALESCE(pr.run_code, 'unknown'))
    END
FROM bags b
LEFT JOIN sterilization_runs sr ON sr.sterilization_run_id = b.sterilization_run_id
LEFT JOIN pasteurization_runs pr ON pr.pasteurization_run_id = b.pasteurization_run_id
WHERE NOT EXISTS (
    SELECT 1
    FROM bag_status_events e
    WHERE e.bag_id = b.bag_id
      AND e.event_type = 'CREATED'
);

INSERT INTO bag_status_events (bag_id, event_type, occurred_at, detail)
SELECT
    b.bag_id,
    'BAG_CODE_ASSIGNED',
    b.labeled_at,
    CONCAT('Printable code assigned: ', b.bag_code)
FROM bags b
WHERE b.labeled_at IS NOT NULL
  AND b.bag_code IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM bag_status_events e
      WHERE e.bag_id = b.bag_id
        AND e.event_type = 'BAG_CODE_ASSIGNED'
  );

INSERT INTO bag_status_events (bag_id, event_type, occurred_at, detail)
SELECT
    b.bag_id,
    'INOCULATED',
    b.inoculated_at,
    CASE
        WHEN b.parent_spawn_bag_id IS NOT NULL
            THEN CONCAT('Inoculated from spawn bag ', COALESCE(parent_bag.bag_code, parent_bag.bag_id))
        WHEN b.source_liquid_culture_id IS NOT NULL
            THEN CONCAT('Inoculated from liquid culture ', COALESCE(lc.culture_code, b.source_liquid_culture_id::TEXT))
        ELSE NULL
    END
FROM bags b
LEFT JOIN bags parent_bag ON parent_bag.bag_id = b.parent_spawn_bag_id
LEFT JOIN liquid_cultures lc ON lc.liquid_culture_id = b.source_liquid_culture_id
WHERE b.inoculated_at IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM bag_status_events e
      WHERE e.bag_id = b.bag_id
        AND e.event_type = 'INOCULATED'
  );

INSERT INTO bag_status_events (bag_id, event_type, occurred_at)
SELECT
    b.bag_id,
    'INCUBATION_STARTED',
    b.incubation_start_at
FROM bags b
WHERE b.incubation_start_at IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM bag_status_events e
      WHERE e.bag_id = b.bag_id
        AND e.event_type = 'INCUBATION_STARTED'
  );

INSERT INTO bag_status_events (bag_id, event_type, occurred_at)
SELECT
    b.bag_id,
    'READY',
    b.ready_at
FROM bags b
WHERE b.ready_at IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM bag_status_events e
      WHERE e.bag_id = b.bag_id
        AND e.event_type = 'READY'
  );

INSERT INTO bag_status_events (bag_id, event_type, occurred_at)
SELECT
    b.bag_id,
    'FRUITING_STARTED',
    b.fruiting_start_at
FROM bags b
WHERE b.fruiting_start_at IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM bag_status_events e
      WHERE e.bag_id = b.bag_id
        AND e.event_type = 'FRUITING_STARTED'
  );

INSERT INTO bag_status_events (bag_id, event_type, occurred_at, detail)
SELECT
    b.bag_id,
    'CONSUMED',
    b.consumed_at,
    'Used as inoculation source'
FROM bags b
WHERE b.consumed_at IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM bag_status_events e
      WHERE e.bag_id = b.bag_id
        AND e.event_type = 'CONSUMED'
  );

INSERT INTO bag_status_events (bag_id, event_type, occurred_at, detail)
SELECT
    b.bag_id,
    'DISPOSED',
    b.disposed_at,
    CONCAT('Reason: ', COALESCE(b.disposal_reason, 'UNKNOWN'))
FROM bags b
WHERE b.disposed_at IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM bag_status_events e
      WHERE e.bag_id = b.bag_id
        AND e.event_type = 'DISPOSED'
  );

INSERT INTO bag_status_events (bag_id, event_type, occurred_at, detail, notes)
SELECT
    h.bag_id,
    'HARVEST_RECORDED',
    h.harvested_at,
    CONCAT('Flush ', h.flush_number, ': ', h.fresh_weight_kg, ' kg'),
    h.notes
FROM harvest_events h
WHERE NOT EXISTS (
    SELECT 1
    FROM bag_status_events e
    WHERE e.bag_id = h.bag_id
      AND e.event_type = 'HARVEST_RECORDED'
      AND e.occurred_at = h.harvested_at
      AND COALESCE(e.detail, '') = CONCAT('Flush ', h.flush_number, ': ', h.fresh_weight_kg, ' kg')
);
