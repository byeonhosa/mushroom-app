# Ingredients + Lots + Batch Add-ins Smoke Test

Run from repo root (`/home/mrmfarm/projects/mushroom-app`).

## 1) Start DB + apply migrations

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

Use a second terminal for requests:

```bash
curl -sS http://127.0.0.1:8000/api/health
```

## 3) Create ingredient + lot

```bash
ING_JSON=$(curl -sS -X POST http://127.0.0.1:8000/api/ingredients \
  -H "Content-Type: application/json" \
  -d '{"name":"Soy Hulls","category":"SUPPLEMENT","notes":"add-in smoke"}')
echo "$ING_JSON"
ING_ID=$(echo "$ING_JSON" | sed -n 's/.*"ingredient_id":\([0-9]\+\).*/\1/p')
```

```bash
LOT_JSON=$(curl -sS -X POST http://127.0.0.1:8000/api/ingredient-lots \
  -H "Content-Type: application/json" \
  -d "{\"ingredient_id\":${ING_ID},\"vendor\":\"FeedCo\",\"lot_code\":\"SH-$(date +%Y%m%d-%H%M%S)\",\"unit_cost_per_kg\":0.8500}")
echo "$LOT_JSON"
LOT_ID=$(echo "$LOT_JSON" | sed -n 's/.*"ingredient_lot_id":\([0-9]\+\).*/\1/p')
```

## 4) Create substrate batch

```bash
BATCH_NAME="SMOKE-ADDINS-$(date +%s)"
BATCH_JSON=$(curl -sS -X POST http://127.0.0.1:8000/api/batches \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"${BATCH_NAME}\",\"substrate_recipe_version_id\":1,\"fill_profile_id\":1,\"bag_count\":4}")
echo "$BATCH_JSON"
BATCH_ID=$(echo "$BATCH_JSON" | sed -n 's/.*"substrate_batch_id":\([0-9]\+\).*/\1/p')
```

## 5) Add add-in with percent only

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/batches/${BATCH_ID}/addins" \
  -H "Content-Type: application/json" \
  -d "{\"ingredient_lot_id\":${LOT_ID},\"pct_of_base_dry\":5.0000,\"notes\":\"pct-only smoke\"}"
```

## 6) Add add-in with kg only

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/batches/${BATCH_ID}/addins" \
  -H "Content-Type: application/json" \
  -d "{\"ingredient_lot_id\":${LOT_ID},\"dry_kg\":0.6500,\"notes\":\"kg-only smoke\"}"
```

## 7) List add-ins

```bash
curl -sS "http://127.0.0.1:8000/api/batches/${BATCH_ID}/addins"
```
