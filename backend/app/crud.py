from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from . import models

def create_fill_profile(db: Session, name: str, dry: float, water: float, notes: str | None):
    fp = models.FillProfile(name=name, target_dry_kg_per_bag=dry, target_water_kg_per_bag=water, notes=notes)
    db.add(fp); db.commit(); db.refresh(fp)
    return fp

def list_fill_profiles(db: Session):
    return db.execute(select(models.FillProfile).order_by(models.FillProfile.fill_profile_id)).scalars().all()

def create_spawn_batch(db: Session, data: dict):
    spawn_batch = models.SpawnBatch(**data)
    db.add(spawn_batch)
    db.commit()
    db.refresh(spawn_batch)
    return spawn_batch

def list_spawn_batches(db: Session):
    return db.execute(
        select(models.SpawnBatch).order_by(models.SpawnBatch.spawn_batch_id.desc())
    ).scalars().all()

def update_spawn_batch(db: Session, spawn_batch_id: int, data: dict):
    spawn_batch = db.get(models.SpawnBatch, spawn_batch_id)
    if not spawn_batch:
        return None
    for k, v in data.items():
        setattr(spawn_batch, k, v)
    db.commit()
    db.refresh(spawn_batch)
    return spawn_batch

def create_substrate_batch(db: Session, data: dict):
    batch = models.SubstrateBatch(**data)
    db.add(batch)
    db.commit()
    db.refresh(batch)

    for i in range(1, batch.bag_count + 1):
        bag_id = f"{batch.name}-{i:04d}"
        db.add(models.SubstrateBag(bag_id=bag_id, substrate_batch_id=batch.substrate_batch_id))
    db.commit()
    return db.get(models.SubstrateBatch, batch.substrate_batch_id)

def create_batch_inoculation(db: Session, data: dict):
    inoc = models.BatchInoculation(**data)
    db.add(inoc)
    db.commit()
    db.refresh(inoc)
    return db.execute(
        select(models.BatchInoculation)
        .options(joinedload(models.BatchInoculation.spawn_batch))
        .where(models.BatchInoculation.batch_inoculation_id == inoc.batch_inoculation_id)
    ).scalar_one()

def list_batch_inoculations(db: Session, substrate_batch_id: int | None = None):
    stmt = (
        select(models.BatchInoculation)
        .options(joinedload(models.BatchInoculation.spawn_batch))
        .order_by(models.BatchInoculation.batch_inoculation_id.desc())
    )
    if substrate_batch_id is not None:
        stmt = stmt.where(models.BatchInoculation.substrate_batch_id == substrate_batch_id)
    return db.execute(stmt).scalars().all()

def get_batch_inoculation_for_batch(db: Session, substrate_batch_id: int):
    return db.execute(
        select(models.BatchInoculation)
        .options(joinedload(models.BatchInoculation.spawn_batch))
        .where(models.BatchInoculation.substrate_batch_id == substrate_batch_id)
    ).scalar_one_or_none()

def update_batch_inoculation(db: Session, batch_inoculation_id: int, data: dict):
    inoc = db.get(models.BatchInoculation, batch_inoculation_id)
    if not inoc:
        return None
    for k, v in data.items():
        setattr(inoc, k, v)
    db.commit()
    return db.execute(
        select(models.BatchInoculation)
        .options(joinedload(models.BatchInoculation.spawn_batch))
        .where(models.BatchInoculation.batch_inoculation_id == batch_inoculation_id)
    ).scalar_one()

def create_pasteurization_run(db: Session, data: dict):
    run = models.PasteurizationRun(**data)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run

def list_pasteurization_runs(db: Session):
    return db.execute(
        select(models.PasteurizationRun).order_by(models.PasteurizationRun.pasteurization_run_id.desc())
    ).scalars().all()

def get_pasteurization_run(db: Session, pasteurization_run_id: int):
    return db.get(models.PasteurizationRun, pasteurization_run_id)

def update_pasteurization_run(db: Session, pasteurization_run_id: int, data: dict):
    run = db.get(models.PasteurizationRun, pasteurization_run_id)
    if not run:
        return None
    for k, v in data.items():
        setattr(run, k, v)
    db.commit()
    db.refresh(run)
    return run

def list_batches(db: Session):
    return db.execute(select(models.SubstrateBatch).order_by(models.SubstrateBatch.substrate_batch_id.desc())).scalars().all()

def get_bags_for_batch(db: Session, substrate_batch_id: int):
    return db.execute(
        select(models.SubstrateBag).where(models.SubstrateBag.substrate_batch_id == substrate_batch_id).order_by(models.SubstrateBag.bag_id)
    ).scalars().all()

def get_bag_detail(db: Session, bag_id: str):
    bag = db.get(models.SubstrateBag, bag_id)
    if not bag:
        return None
    _ = bag.harvest_events
    return bag

def create_harvest_event(db: Session, data: dict):
    ev = models.HarvestEvent(**data)
    db.add(ev); db.commit(); db.refresh(ev)
    return ev

def batch_metrics(db: Session, substrate_batch_id: int):
    batch = db.get(models.SubstrateBatch, substrate_batch_id)
    if not batch:
        return None

    total_harvest = db.execute(
        select(func.coalesce(func.sum(models.HarvestEvent.fresh_weight_kg), 0))
        .join(models.SubstrateBag, models.SubstrateBag.bag_id == models.HarvestEvent.bag_id)
        .where(models.SubstrateBag.substrate_batch_id == substrate_batch_id)
    ).scalar_one()

    dry_per_bag = float(batch.fill_profile.target_dry_kg_per_bag)
    dry_total = dry_per_bag * batch.bag_count
    be = (float(total_harvest) / dry_total * 100.0) if dry_total > 0 else 0.0

    return {
        "substrate_batch_id": substrate_batch_id,
        "total_harvest_kg": float(total_harvest),
        "dry_kg_total": float(dry_total),
        "be_percent": float(be),
    }
