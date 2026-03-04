from typing import Literal
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from psycopg.errors import UniqueViolation

from .db import get_db
from . import schemas, crud

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}


# --- Reference data ---

@router.get("/fill-profiles", response_model=list[schemas.FillProfileOut])
def fill_profiles(db: Session = Depends(get_db)):
    return crud.list_fill_profiles(db)


@router.post("/fill-profiles", response_model=schemas.FillProfileOut)
def create_fill_profile(payload: schemas.FillProfileCreate, db: Session = Depends(get_db)):
    return crud.create_fill_profile(
        db, payload.name, payload.target_dry_kg_per_bag,
        payload.target_water_kg_per_bag, payload.notes
    )


@router.get("/substrate-recipe-versions", response_model=list[schemas.SubstrateRecipeVersionOut])
def list_substrate_recipe_versions(db: Session = Depends(get_db)):
    return crud.list_substrate_recipe_versions(db)


@router.get("/spawn-recipes", response_model=list[schemas.SpawnRecipeOut])
def list_spawn_recipes(db: Session = Depends(get_db)):
    return crud.list_spawn_recipes(db)


@router.get("/mix-lots", response_model=list[schemas.MixLotOut])
def list_mix_lots(db: Session = Depends(get_db)):
    return crud.list_mix_lots(db)


@router.post("/mix-lots", response_model=schemas.MixLotOut)
def create_mix_lot(payload: schemas.MixLotCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_mix_lot(db, payload.model_dump(exclude_unset=True))
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(409, "Mix lot code already exists.")
        raise


@router.get("/species", response_model=list[schemas.MushroomSpeciesOut])
def list_species(active_only: bool = True, db: Session = Depends(get_db)):
    return crud.list_species(db, active_only=active_only)


@router.post("/species", response_model=schemas.MushroomSpeciesOut)
def create_species(payload: schemas.MushroomSpeciesCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_species(db, payload.model_dump(exclude_unset=True))
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(409, "Species code already exists.")
        raise


@router.get("/grain-types", response_model=list[schemas.GrainTypeOut])
def list_grain_types(db: Session = Depends(get_db)):
    return crud.list_grain_types(db)


@router.post("/grain-types", response_model=schemas.GrainTypeOut)
def create_grain_type(payload: schemas.GrainTypeCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_grain_type(db, payload.model_dump(exclude_unset=True))
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(409, "Grain type already exists.")
        raise


# --- Pasteurization runs ---

@router.get("/pasteurization-runs", response_model=list[schemas.PasteurizationRunOut])
def list_pasteurization_runs(db: Session = Depends(get_db)):
    return crud.list_pasteurization_runs(db)


@router.post("/pasteurization-runs", response_model=schemas.PasteurizationRunOut)
def create_pasteurization_run(payload: schemas.PasteurizationRunCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_pasteurization_run(db, payload.model_dump(exclude_unset=True))
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(409, "Run code already exists.")
        raise


@router.get("/pasteurization-runs/{run_id}", response_model=schemas.PasteurizationRunOut)
def get_pasteurization_run(run_id: int, db: Session = Depends(get_db)):
    r = crud.get_pasteurization_run(db, run_id)
    if not r:
        raise HTTPException(404, "Pasteurization run not found")
    return r


# --- Sterilization runs ---

@router.get("/sterilization-runs", response_model=list[schemas.SterilizationRunOut])
def list_sterilization_runs(
    run_code_contains: str | None = None,
    sort_by: str = "sterilization_run_id",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
):
    return crud.list_sterilization_runs(db, run_code_contains=run_code_contains, sort_by=sort_by, sort_order=sort_order)


@router.post("/sterilization-runs", response_model=schemas.SterilizationRunOut)
def create_sterilization_run(payload: schemas.SterilizationRunCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_sterilization_run(db, payload.model_dump(exclude_unset=True))
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(409, "Run code already exists.")
        raise


@router.get("/sterilization-runs/{run_id}", response_model=schemas.SterilizationRunOut)
def get_sterilization_run(run_id: int, db: Session = Depends(get_db)):
    r = crud.get_sterilization_run(db, run_id)
    if not r:
        raise HTTPException(404, "Sterilization run not found")
    return r


# --- Bags ---

@router.post("/bags/spawn", response_model=list[schemas.BagOut])
def create_spawn_bags(payload: schemas.BagCreateSpawn, db: Session = Depends(get_db)):
    try:
        bags = crud.create_spawn_bags(
            db, payload.sterilization_run_id, payload.species_id, payload.bag_count
        )
        return bags
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/bags/substrate", response_model=list[schemas.BagOut])
def create_substrate_bags(payload: schemas.BagCreateSubstrate, db: Session = Depends(get_db)):
    try:
        bags = crud.create_substrate_bags(
            db, payload.pasteurization_run_id, payload.species_id, payload.bag_count
        )
        return bags
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/bags", response_model=list[schemas.BagOut])
def list_bags(
    bag_type: str | None = None,
    species_id: int | None = None,
    pasteurization_run_id: int | None = None,
    sterilization_run_id: int | None = None,
    status: str | None = None,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    return crud.list_bags(
        db,
        bag_type=bag_type,
        species_id=species_id,
        pasteurization_run_id=pasteurization_run_id,
        sterilization_run_id=sterilization_run_id,
        status=status,
        limit=limit,
    )


@router.get("/bags/{bag_id}", response_model=schemas.BagDetailOut)
def get_bag(bag_id: str, db: Session = Depends(get_db)):
    bag = crud.get_bag_detail(db, bag_id)
    if not bag:
        raise HTTPException(404, "Bag not found")
    return bag


# --- Event recording (scan flow) ---

@router.post("/bags/{bag_id}/incubation-start", response_model=schemas.BagOut)
def record_incubation_start(bag_id: str, db: Session = Depends(get_db)):
    bag = crud.update_bag_incubation_start(db, bag_id)
    if not bag:
        raise HTTPException(404, "Bag not found")
    return bag


@router.post("/bags/{bag_id}/fruiting-start", response_model=schemas.BagOut)
def record_fruiting_start(bag_id: str, db: Session = Depends(get_db)):
    try:
        bag = crud.update_bag_fruiting_start(db, bag_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not bag:
        raise HTTPException(404, "Bag not found")
    return bag


class DisposalBody(BaseModel):
    disposal_reason: Literal["CONTAMINATION", "FINAL_HARVEST"]


@router.post("/bags/{bag_id}/disposal", response_model=schemas.BagOut)
def record_disposal(
    bag_id: str,
    payload: DisposalBody,
    db: Session = Depends(get_db),
):
    bag = crud.update_bag_disposal(db, bag_id, payload.disposal_reason)
    if not bag:
        raise HTTPException(404, "Bag not found")
    return bag


# --- Inoculations ---

@router.post("/inoculations", response_model=schemas.InoculationOut)
def create_inoculation(payload: schemas.InoculationCreate, db: Session = Depends(get_db)):
    try:
        inoc = crud.create_inoculation(
            db,
            payload.substrate_bag_id,
            payload.spawn_bag_id,
            inoculated_at=payload.inoculated_at,
        )
        return inoc
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise HTTPException(409, "Substrate bag already inoculated.")
        raise


@router.get("/bags/{bag_id}/inoculation", response_model=schemas.InoculationOut)
def get_inoculation_for_bag(bag_id: str, db: Session = Depends(get_db)):
    inoc = crud.get_inoculation_for_substrate_bag(db, bag_id)
    if not inoc:
        raise HTTPException(404, "Inoculation not found")
    return inoc


# --- Harvest events ---

@router.post("/harvest-events", response_model=schemas.HarvestEventOut)
def create_harvest_event(payload: schemas.HarvestEventCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_harvest_event(
            db,
            payload.bag_id,
            payload.flush_number,
            payload.fresh_weight_kg,
            harvested_at=payload.harvested_at,
            notes=payload.notes,
        )
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except IntegrityError as e:
        raise HTTPException(409, "Flush already recorded for this bag.")


@router.get("/bags/{bag_id}/harvest-events", response_model=list[schemas.HarvestEventOut])
def list_harvest_events(bag_id: str, db: Session = Depends(get_db)):
    return crud.list_harvest_events_for_bag(db, bag_id)


# --- Labels (QR + human-readable) ---

@router.get("/labels/{bag_id}/qr")
def get_label_qr(bag_id: str, db: Session = Depends(get_db)):
    """Return QR code image for a bag (SVG or PNG)."""
    bag = crud.get_bag(db, bag_id)
    if not bag:
        raise HTTPException(404, "Bag not found")
    try:
        import qrcode
        import io
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(bag_id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except ImportError:
        raise HTTPException(501, "QR code generation not available (install qrcode[pil])")


@router.get("/labels/{bag_id}")
def get_label_data(bag_id: str, db: Session = Depends(get_db)):
    """Return bag_id for label (QR content + human-readable text)."""
    bag = crud.get_bag(db, bag_id)
    if not bag:
        raise HTTPException(404, "Bag not found")
    return {"bag_id": bag_id}
