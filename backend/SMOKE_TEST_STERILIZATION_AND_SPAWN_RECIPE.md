# Sterilization Runs + Spawn Recipe Smoke Test

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

## 3) Create sterilization run

```bash
RUN_CODE="AUTO-$(date +%Y%m%d-%H%M%S)-A"
STER_JSON=$(curl -sS -X POST http://127.0.0.1:8000/api/sterilization-runs \
  -H "Content-Type: application/json" \
  -d "{\"run_code\":\"${RUN_CODE}\",\"cycle_start_at\":\"2026-02-16T10:00:00Z\",\"cycle_end_at\":\"2026-02-16T12:00:00Z\",\"unloaded_at\":\"2026-02-16T12:30:00Z\",\"temp_c\":121.00,\"psi\":15.00,\"hold_minutes\":120,\"notes\":\"smoke\"}")
echo "$STER_JSON"
STER_ID=$(echo "$STER_JSON" | sed -n 's/.*"sterilization_run_id":\([0-9]\+\).*/\1/p')
```

## 4) Create grain type (if needed)

```bash
GRAIN_JSON=$(curl -sS -X POST http://127.0.0.1:8000/api/grain-types \
  -H "Content-Type: application/json" \
  -d '{"name":"Millet","notes":"smoke grain type"}' || true)
echo "$GRAIN_JSON"
```

```bash
GRAIN_ID=$(curl -sS http://127.0.0.1:8000/api/grain-types | sed -n 's/.*"grain_type_id":\([0-9]\+\).*"name":"Rye".*/\1/p' | head -n 1)
echo "Using grain_type_id=${GRAIN_ID}"
```

## 5) Create IN_HOUSE_GRAIN spawn batch with recipe + sterilization_run_id

```bash
curl -sS -X POST http://127.0.0.1:8000/api/spawn-batches \
  -H "Content-Type: application/json" \
  -d "{\"spawn_type\":\"IN_HOUSE_GRAIN\",\"strain_code\":\"LM\",\"sterilization_run_id\":${STER_ID},\"grain_type_id\":${GRAIN_ID},\"grain_kg\":6.500,\"vermiculite_kg\":1.250,\"water_kg\":5.400,\"supplement_kg\":0.200,\"notes\":\"in-house smoke\"}"
```

## 6) Create PURCHASED_BLOCK spawn batch without recipe fields

```bash
curl -sS -X POST http://127.0.0.1:8000/api/spawn-batches \
  -H "Content-Type: application/json" \
  -d '{"spawn_type":"PURCHASED_BLOCK","strain_code":"PO","vendor":"VendorA","lot_code":"LOT-123","notes":"purchased smoke"}'
```

## 7) Verify GET endpoints

```bash
curl -sS http://127.0.0.1:8000/api/sterilization-runs
```

```bash
curl -sS http://127.0.0.1:8000/api/grain-types
```

```bash
curl -sS http://127.0.0.1:8000/api/spawn-batches
```
