from sqlalchemy.exc import IntegrityError
from psycopg.errors import UniqueViolation
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .db import get_db
from . import schemas, crud

router = APIRouter()

@router.get("/health")
def health():
    return {"ok": True}

@router.get("/fill-profiles", response_model=list[schemas.FillProfileOut])
def fill_profiles(db: Session = Depends(get_db)):
    return crud.list_fill_profiles(db)

@router.post("/fill-profiles", response_model=schemas.FillProfileOut)
def create_fill_profile(payload: schemas.FillProfileCreate, db: Session = Depends(get_db)):
    return crud.create_fill_profile(db, payload.name, payload.target_dry_kg_per_bag, payload.target_water_kg_per_bag, payload.notes)

@router.get("/spawn-batches", response_model=list[schemas.SpawnBatchOut])
def list_spawn_batches(db: Session = Depends(get_db)):
    return crud.list_spawn_batches(db)

@router.post("/spawn-batches", response_model=schemas.SpawnBatchOut)
def create_spawn_batch(payload: schemas.SpawnBatchCreate, db: Session = Depends(get_db)):
    return crud.create_spawn_batch(db, payload.model_dump(exclude_unset=True))

@router.patch("/spawn-batches/{spawn_batch_id}", response_model=schemas.SpawnBatchOut)
def update_spawn_batch(spawn_batch_id: int, payload: schemas.SpawnBatchUpdate, db: Session = Depends(get_db)):
    spawn_batch = crud.update_spawn_batch(db, spawn_batch_id, payload.model_dump(exclude_unset=True))
    if not spawn_batch:
        raise HTTPException(404, "Spawn batch not found")
    return spawn_batch

@router.get("/pasteurization-runs", response_model=list[schemas.PasteurizationRunOut])
def list_pasteurization_runs(db: Session = Depends(get_db)):
    return crud.list_pasteurization_runs(db)

@router.post("/pasteurization-runs", response_model=schemas.PasteurizationRunOut)
def create_pasteurization_run(payload: schemas.PasteurizationRunCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_pasteurization_run(db, payload.model_dump(exclude_unset=True))
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(status_code=409, detail="Run code already exists. Choose a unique run code.")
        raise

@router.get("/pasteurization-runs/{run_id}", response_model=schemas.PasteurizationRunOut)
def get_pasteurization_run(run_id: int, db: Session = Depends(get_db)):
    run = crud.get_pasteurization_run(db, run_id)
    if not run:
        raise HTTPException(404, "Pasteurization run not found")
    return run

@router.patch("/pasteurization-runs/{run_id}", response_model=schemas.PasteurizationRunOut)
def update_pasteurization_run(run_id: int, payload: schemas.PasteurizationRunUpdate, db: Session = Depends(get_db)):
    run = crud.update_pasteurization_run(db, run_id, payload.model_dump(exclude_unset=True))
    if not run:
        raise HTTPException(404, "Pasteurization run not found")
    return run

@router.get("/batches", response_model=list[schemas.SubstrateBatchOut])
def list_batches(db: Session = Depends(get_db)):
    return crud.list_batches(db)

@router.post("/batches", response_model=schemas.SubstrateBatchOut)
def create_batch(payload: schemas.SubstrateBatchCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_substrate_batch(db, payload.model_dump(exclude_unset=True))
    except IntegrityError as e:
        # Unique batch name violation -> 409 conflict
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(status_code=409, detail="Batch name already exists. Choose a unique batch name.")
        raise

@router.get("/batch-inoculations", response_model=list[schemas.BatchInoculationDetailOut])
def list_batch_inoculations(substrate_batch_id: int | None = None, db: Session = Depends(get_db)):
    return crud.list_batch_inoculations(db, substrate_batch_id)

@router.post("/batch-inoculations", response_model=schemas.BatchInoculationDetailOut)
def create_batch_inoculation(payload: schemas.BatchInoculationCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_batch_inoculation(db, payload.model_dump(exclude_unset=True))
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(status_code=409, detail="Batch already has an inoculation record.")
        raise

@router.patch("/batch-inoculations/{batch_inoculation_id}", response_model=schemas.BatchInoculationDetailOut)
def update_batch_inoculation(
    batch_inoculation_id: int,
    payload: schemas.BatchInoculationUpdate,
    db: Session = Depends(get_db)
):
    try:
        inoc = crud.update_batch_inoculation(db, batch_inoculation_id, payload.model_dump(exclude_unset=True))
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(status_code=409, detail="Batch already has an inoculation record.")
        raise
    if not inoc:
        raise HTTPException(404, "Batch inoculation not found")
    return inoc

@router.get("/batches/{batch_id}/inoculation", response_model=schemas.BatchInoculationDetailOut)
def get_batch_inoculation(batch_id: int, db: Session = Depends(get_db)):
    inoc = crud.get_batch_inoculation_for_batch(db, batch_id)
    if not inoc:
        raise HTTPException(404, "Batch inoculation not found")
    return inoc

@router.get("/batches/{batch_id}/bags", response_model=list[schemas.SubstrateBagOut])
def list_batch_bags(batch_id: int, db: Session = Depends(get_db)):
    return crud.get_bags_for_batch(db, batch_id)

@router.get("/batches/{batch_id}/metrics", response_model=schemas.BatchMetricsOut)
def get_batch_metrics(batch_id: int, db: Session = Depends(get_db)):
    m = crud.batch_metrics(db, batch_id)
    if not m:
        raise HTTPException(404, "Batch not found")
    return m

@router.get("/bags/{bag_id}", response_model=schemas.BagDetailOut)
def bag_detail(bag_id: str, db: Session = Depends(get_db)):
    bag = crud.get_bag_detail(db, bag_id)
    if not bag:
        raise HTTPException(404, "Bag not found")
    return bag

@router.post("/harvest-events", response_model=schemas.HarvestEventOut)
def create_harvest(payload: schemas.HarvestEventCreate, db: Session = Depends(get_db)):
    return crud.create_harvest_event(db, payload.model_dump(exclude_unset=True))
