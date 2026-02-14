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
