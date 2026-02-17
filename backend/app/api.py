from sqlalchemy.exc import IntegrityError
from psycopg.errors import UniqueViolation
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Literal
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

@router.get("/grain-types", response_model=list[schemas.GrainTypeOut])
def list_grain_types(db: Session = Depends(get_db)):
    return crud.list_grain_types(db)

@router.post("/grain-types", response_model=schemas.GrainTypeOut)
def create_grain_type(payload: schemas.GrainTypeCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_grain_type(db, payload.model_dump(exclude_unset=True))
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(status_code=409, detail="Grain type name already exists.")
        raise

@router.patch("/grain-types/{grain_type_id}", response_model=schemas.GrainTypeOut)
def update_grain_type(grain_type_id: int, payload: schemas.GrainTypeUpdate, db: Session = Depends(get_db)):
    try:
        grain_type = crud.update_grain_type(db, grain_type_id, payload.model_dump(exclude_unset=True))
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(status_code=409, detail="Grain type name already exists.")
        raise
    if not grain_type:
        raise HTTPException(404, "Grain type not found")
    return grain_type

@router.get("/sterilization-runs", response_model=list[schemas.SterilizationRunOut])
def list_sterilization_runs(
    run_code_contains: str | None = None,
    unloaded_from: datetime | None = None,
    unloaded_to: datetime | None = None,
    sort_by: Literal["sterilization_run_id", "run_code", "unloaded_at"] = "sterilization_run_id",
    sort_order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
):
    return crud.list_sterilization_runs(
        db,
        run_code_contains=run_code_contains,
        unloaded_from=unloaded_from,
        unloaded_to=unloaded_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )

@router.post("/sterilization-runs", response_model=schemas.SterilizationRunOut)
def create_sterilization_run(payload: schemas.SterilizationRunCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_sterilization_run(db, payload.model_dump(exclude_unset=True))
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(status_code=409, detail="Run code already exists. Choose a unique run code.")
        raise

@router.get("/sterilization-runs/{run_id}", response_model=schemas.SterilizationRunOut)
def get_sterilization_run(run_id: int, db: Session = Depends(get_db)):
    run = crud.get_sterilization_run(db, run_id)
    if not run:
        raise HTTPException(404, "Sterilization run not found")
    return run

@router.patch("/sterilization-runs/{run_id}", response_model=schemas.SterilizationRunOut)
def update_sterilization_run(run_id: int, payload: schemas.SterilizationRunUpdate, db: Session = Depends(get_db)):
    run = crud.update_sterilization_run(db, run_id, payload.model_dump(exclude_unset=True))
    if not run:
        raise HTTPException(404, "Sterilization run not found")
    return run

@router.get("/ingredients", response_model=list[schemas.IngredientOut])
def list_ingredients(db: Session = Depends(get_db)):
    return crud.list_ingredients(db)

@router.post("/ingredients", response_model=schemas.IngredientOut)
def create_ingredient(payload: schemas.IngredientCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_ingredient(db, payload.model_dump(exclude_unset=True))
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(status_code=409, detail="Ingredient name already exists.")
        raise

@router.patch("/ingredients/{ingredient_id}", response_model=schemas.IngredientOut)
def update_ingredient(ingredient_id: int, payload: schemas.IngredientUpdate, db: Session = Depends(get_db)):
    try:
        ingredient = crud.update_ingredient(db, ingredient_id, payload.model_dump(exclude_unset=True))
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(status_code=409, detail="Ingredient name already exists.")
        raise
    if not ingredient:
        raise HTTPException(404, "Ingredient not found")
    return ingredient

@router.get("/ingredient-lots", response_model=list[schemas.IngredientLotOut])
def list_ingredient_lots(ingredient_id: int | None = None, db: Session = Depends(get_db)):
    return crud.list_ingredient_lots(db, ingredient_id)

@router.post("/ingredient-lots", response_model=schemas.IngredientLotOut)
def create_ingredient_lot(payload: schemas.IngredientLotCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_ingredient_lot(db, payload.model_dump(exclude_unset=True))
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Invalid ingredient_lot payload.")

@router.patch("/ingredient-lots/{ingredient_lot_id}", response_model=schemas.IngredientLotOut)
def update_ingredient_lot(ingredient_lot_id: int, payload: schemas.IngredientLotUpdate, db: Session = Depends(get_db)):
    try:
        ingredient_lot = crud.update_ingredient_lot(db, ingredient_lot_id, payload.model_dump(exclude_unset=True))
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Invalid ingredient_lot payload.")
    if not ingredient_lot:
        raise HTTPException(404, "Ingredient lot not found")
    return ingredient_lot

@router.get("/spawn-batches", response_model=list[schemas.SpawnBatchOut])
def list_spawn_batches(
    spawn_type: Literal["PURCHASED_BLOCK", "IN_HOUSE_GRAIN"] | None = None,
    strain_contains: str | None = None,
    grain_type_id: int | None = None,
    sterilization_run_id: int | None = None,
    sort_by: Literal["spawn_batch_id", "made_at", "incubation_start_at", "strain_code"] = "spawn_batch_id",
    sort_order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
):
    return crud.list_spawn_batches(
        db,
        spawn_type=spawn_type,
        strain_contains=strain_contains,
        grain_type_id=grain_type_id,
        sterilization_run_id=sterilization_run_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )

@router.post("/spawn-batches", response_model=schemas.SpawnBatchOut)
def create_spawn_batch(payload: schemas.SpawnBatchCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_spawn_batch(db, payload.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/spawn-batches/{spawn_batch_id}", response_model=schemas.SpawnBatchOut)
def update_spawn_batch(spawn_batch_id: int, payload: schemas.SpawnBatchUpdate, db: Session = Depends(get_db)):
    try:
        spawn_batch = crud.update_spawn_batch(db, spawn_batch_id, payload.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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

@router.get("/batches/{batch_id}/addins", response_model=list[schemas.SubstrateBatchAddinOut])
def list_batch_addins(batch_id: int, db: Session = Depends(get_db)):
    return crud.list_substrate_batch_addins(db, batch_id)

@router.post("/batches/{batch_id}/addins", response_model=schemas.SubstrateBatchAddinOut)
def create_batch_addin(batch_id: int, payload: schemas.SubstrateBatchAddinCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_substrate_batch_addin(db, batch_id, payload.model_dump(exclude_unset=True))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/batches/{batch_id}/addins/{substrate_batch_addin_id}")
def delete_batch_addin(batch_id: int, substrate_batch_addin_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_substrate_batch_addin(db, batch_id, substrate_batch_addin_id)
    if not deleted:
        raise HTTPException(404, "Batch add-in not found")
    return {"ok": True}

@router.get("/bags/{bag_id}", response_model=schemas.BagDetailOut)
def bag_detail(bag_id: str, db: Session = Depends(get_db)):
    bag = crud.get_bag_detail(db, bag_id)
    if not bag:
        raise HTTPException(404, "Bag not found")
    return bag

@router.post("/harvest-events", response_model=schemas.HarvestEventOut)
def create_harvest(payload: schemas.HarvestEventCreate, db: Session = Depends(get_db)):
    return crud.create_harvest_event(db, payload.model_dump(exclude_unset=True))

@router.post("/harvests", response_model=schemas.HarvestOut)
def create_harvest_from_batch(payload: schemas.HarvestCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_harvest_from_batch(db, payload.model_dump(exclude_unset=True))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
