INSERT INTO bag_status_events (bag_id, event_type, occurred_at, detail)
SELECT
    b.bag_id,
    'STERILIZED',
    GREATEST(COALESCE(sr.unloaded_at, b.created_at), b.created_at),
    CONCAT('Sterilization run completed: ', COALESCE(sr.run_code, 'unknown'))
FROM bags b
LEFT JOIN sterilization_runs sr ON sr.sterilization_run_id = b.sterilization_run_id
WHERE b.bag_type = 'SPAWN'
  AND b.sterilization_run_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM bag_status_events e
      WHERE e.bag_id = b.bag_id
        AND e.event_type = 'STERILIZED'
  );

INSERT INTO bag_status_events (bag_id, event_type, occurred_at, detail)
SELECT
    b.bag_id,
    'PASTEURIZED',
    GREATEST(COALESCE(pr.unloaded_at, b.created_at), b.created_at),
    CONCAT('Pasteurization run completed: ', COALESCE(pr.run_code, 'unknown'))
FROM bags b
LEFT JOIN pasteurization_runs pr ON pr.pasteurization_run_id = b.pasteurization_run_id
WHERE b.bag_type = 'SUBSTRATE'
  AND b.pasteurization_run_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM bag_status_events e
      WHERE e.bag_id = b.bag_id
        AND e.event_type = 'PASTEURIZED'
  );
