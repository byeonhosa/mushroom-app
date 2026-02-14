from sqlalchemy.orm import Session
from sqlalchemy import select, func
from . import models

def create_fill_profile(db: Session, name: str, dry: float, water: float, notes: str | None):
    fp = models.FillProfile(name=name, target_dry_kg_per_bag=dry, target_water_kg_per_bag=water, notes=notes)
    db.add(fp); db.commit(); db.refresh(fp)
    return fp

def list_fill_profiles(db: Session):
    return db.execute(select(models.FillProfile).order_by(models.FillProfile.fill_profile_id)).scalars().all()

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
