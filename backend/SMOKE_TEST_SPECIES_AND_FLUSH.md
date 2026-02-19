# Smoke Test: Species + Block Harvest Flush Integrity

Assumes API is running at `http://127.0.0.1:8000`.

## 1) Create species

```bash
curl -sS -X POST http://127.0.0.1:8000/api/species \
  -H 'Content-Type: application/json' \
  -d '{"code":"LM","name":"Lions Mane","latin_name":"Hericium erinaceus"}'
```

## 2) Create substrate block with species_id

Replace `SPECIES_ID` with the `species_id` from step 1.

```bash
curl -sS -X POST http://127.0.0.1:8000/api/blocks \
  -H 'Content-Type: application/json' \
  -d '{"block_type":"SUBSTRATE","species_id":SPECIES_ID}'
```

## 3) Create harvest flush 1

Replace `BLOCK_ID` with the `block_id` from step 2.

```bash
curl -i -sS -X POST http://127.0.0.1:8000/api/harvest-events \
  -H 'Content-Type: application/json' \
  -d '{"block_id":BLOCK_ID,"flush_number":1,"fresh_weight_kg":0.500,"notes":"flush 1"}'
```

## 4) Attempt duplicate flush 1 (expect 409)

```bash
curl -i -sS -X POST http://127.0.0.1:8000/api/harvest-events \
  -H 'Content-Type: application/json' \
  -d '{"block_id":BLOCK_ID,"flush_number":1,"fresh_weight_kg":0.450,"notes":"duplicate flush 1"}'
```

Expected: `HTTP/1.1 409 Conflict` and message `Flush already recorded for this block.`

## 5) Verify existing harvest events for block

```bash
curl -sS http://127.0.0.1:8000/api/blocks/BLOCK_ID/harvest-events
```
