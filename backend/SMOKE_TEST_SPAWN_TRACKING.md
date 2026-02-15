# Spawn Tracking + Batch Inoculation Smoke Test

Run from repo root (`/home/mrmfarm/projects/mushroom-app`).

## 1) Start database + apply migrations

```bash
docker compose up -d db
cd backend
. .venv/bin/activate
python -m app.migrate
```

## 2) Start API

```bash
cd /home/mrmfarm/projects/mushroom-app/backend
. .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open a second terminal for the requests below.

## 3) Spawn batch create/list/update

```bash
curl -sS http://127.0.0.1:8000/api/health
```

```bash
SPAWN_JSON=$(curl -sS -X POST http://127.0.0.1:8000/api/spawn-batches \
  -H "Content-Type: application/json" \
  -d '{"spawn_type":"PURCHASED_BLOCK","strain_code":"LM","vendor":"MycoVendor","lot_code":"LOT-001","notes":"smoke"}')
echo "$SPAWN_JSON"
SPAWN_ID=$(echo "$SPAWN_JSON" | sed -n 's/.*"spawn_batch_id":\([0-9]\+\).*/\1/p')
```

```bash
curl -sS -X PATCH "http://127.0.0.1:8000/api/spawn-batches/${SPAWN_ID}" \
  -H "Content-Type: application/json" \
  -d '{"vendor":"MycoVendor-Updated"}'
```

```bash
curl -sS http://127.0.0.1:8000/api/spawn-batches
```

## 4) Batch + inoculation attribution

Create an in-house grain spawn batch (includes Iteration A fields):

```bash
INHOUSE_SPAWN_JSON=$(curl -sS -X POST http://127.0.0.1:8000/api/spawn-batches \
  -H "Content-Type: application/json" \
  -d '{"spawn_type":"IN_HOUSE_GRAIN","strain_code":"LM","grain_dry_kg":6.500,"grain_water_kg":5.850,"supplement_kg":0.250,"lc_vendor":"LabA","lc_code":"LC-LM-20260215","sterilization_run_code":"ST-20260215-A","incubation_zone_id":2,"notes":"in-house grain smoke"}')
echo "$INHOUSE_SPAWN_JSON"
INHOUSE_SPAWN_ID=$(echo "$INHOUSE_SPAWN_JSON" | sed -n 's/.*"spawn_batch_id":\([0-9]\+\).*/\1/p')
```

```bash
BATCH_NAME="SMOKE-BATCH-SPAWN-$(date +%s)"
BATCH_JSON=$(curl -sS -X POST http://127.0.0.1:8000/api/batches \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"${BATCH_NAME}\",\"substrate_recipe_version_id\":1,\"fill_profile_id\":1,\"bag_count\":2}")
echo "$BATCH_JSON"
BATCH_ID=$(echo "$BATCH_JSON" | sed -n 's/.*"substrate_batch_id":\([0-9]\+\).*/\1/p')
```

```bash
curl -sS -X POST http://127.0.0.1:8000/api/batch-inoculations \
  -H "Content-Type: application/json" \
  -d "{\"substrate_batch_id\":${BATCH_ID},\"spawn_batch_id\":${INHOUSE_SPAWN_ID},\"spawn_blocks_used\":2}"
```

```bash
curl -sS "http://127.0.0.1:8000/api/batch-inoculations?substrate_batch_id=${BATCH_ID}"
```

```bash
curl -sS "http://127.0.0.1:8000/api/batches/${BATCH_ID}/inoculation"
```

## 5) Verify duplicate inoculation returns 409

```bash
curl -i -sS -X POST http://127.0.0.1:8000/api/batch-inoculations \
  -H "Content-Type: application/json" \
  -d "{\"substrate_batch_id\":${BATCH_ID},\"spawn_batch_id\":${INHOUSE_SPAWN_ID},\"spawn_blocks_used\":3}"
```
