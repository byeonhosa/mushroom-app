"""
Bag lifecycle operations: creation, retrieval, inoculation, lifecycle events,
harvest recording, label generation, and lineage traversal.
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from . import models, bag_id
from .crud_status import (
    _now,
    _as_utc,
    _bag_history_snapshot,
    _sync_bag_status,
    _record_bag_event,
    _resolve_bag,
    _bag_lineage_options,
    _build_descendant_bags,
)
from .crud_reporting import (
    _bag_payload,
    _build_lineage_row,
    _summarize_bags,
)


def _format_harvest_event_detail(flush_number: int, fresh_weight_kg: float) -> str:
    return f"Flush {flush_number}: {fresh_weight_kg:.3f} kg"


def _build_status_event_row(event: models.BagStatusEvent) -> dict:
    return {
        "bag_status_event_id": event.bag_status_event_id,
        "bag_id": event.bag_id,
        "event_type": event.event_type,
        "occurred_at": _as_utc(event.occurred_at),
        "detail": event.detail,
        "notes": event.notes,
    }


def _count_bags_for_run(db: Session, run_column, run_id: int) -> int:
    return db.execute(
        select(func.count())
        .select_from(models.Bag)
        .where(run_column == run_id)
    ).scalar_one()


def _validate_run_capacity(run_label: str, planned_bag_count: int, existing_bag_count: int, requested_bag_count: int):
    next_total = existing_bag_count + requested_bag_count
    if next_total > planned_bag_count:
        raise ValueError(
            f"{run_label} is planned for {planned_bag_count} bag(s), but this would create {next_total} total records"
        )


def _get_unlabeled_bags_for_run(
    db: Session,
    *,
    bag_type: str,
    run_column,
    run_id: int,
    bag_count: int,
) -> list[models.Bag]:
    bags = db.execute(
        select(models.Bag)
        .where(
            models.Bag.bag_type == bag_type,
            run_column == run_id,
            models.Bag.bag_code.is_(None),
        )
        .order_by(models.Bag.created_at.asc(), models.Bag.bag_id.asc())
        .limit(bag_count)
    ).scalars().all()
    if len(bags) < bag_count:
        raise ValueError(f"Requested {bag_count} bags but only {len(bags)} unlabeled {bag_type.lower()} bag(s) are available")
    return bags


def _resolve_spawn_source(db: Session, spawn_bag_ref: str) -> models.Bag:
    spawn = _resolve_bag(db, spawn_bag_ref)
    if not spawn:
        raise LookupError("Spawn bag not found")
    if spawn.bag_type != "SPAWN":
        raise ValueError("Spawn bag must be SPAWN type")
    snapshot = _bag_history_snapshot(spawn)
    if snapshot["consumed_at"]:
        raise ValueError("Spawn bag is already consumed")
    if not snapshot["ready_at"]:
        raise ValueError("Spawn bag must be READY before it can inoculate other bags")
    if spawn.species_id is None:
        raise ValueError("Spawn bag must have an assigned species before it can inoculate other bags")
    return spawn


def list_bag_status_events(db: Session, bag_ref: str):
    bag = _resolve_bag(db, bag_ref)
    if not bag:
        return []
    return db.execute(
        select(models.BagStatusEvent)
        .where(models.BagStatusEvent.bag_id == bag.bag_id)
        .order_by(models.BagStatusEvent.occurred_at.asc(), models.BagStatusEvent.bag_status_event_id.asc())
    ).scalars().all()


def create_spawn_bags(db: Session, sterilization_run_id: int, bag_count: int) -> list[models.Bag]:
    run = db.get(models.SterilizationRun, sterilization_run_id)
    if not run:
        raise ValueError(f"Sterilization run {sterilization_run_id} not found")
    existing_bag_count = _count_bags_for_run(db, models.Bag.sterilization_run_id, sterilization_run_id)
    _validate_run_capacity(f"Sterilization run {run.run_code}", run.bag_count, existing_bag_count, bag_count)
    ids = bag_id.generate_internal_bag_ids(db, "SPAWN", bag_count)
    bags = []
    created_at = _now()
    process_stage_at = max(_as_utc(run.unloaded_at) or created_at, created_at)
    for bid in ids:
        bag = models.Bag(
            bag_id=bid,
            bag_type="SPAWN",
            bag_code=None,
            species_id=None,
            sterilization_run_id=sterilization_run_id,
            pasteurization_run_id=None,
            mix_lot_id=None,
            substrate_recipe_version_id=None,
            spawn_recipe_id=run.spawn_recipe_id,
            grain_type_id=run.grain_type_id,
            created_at=created_at,
            labeled_at=None,
            inoculated_at=None,
            status="STERILIZED",
        )
        db.add(bag)
        _record_bag_event(
            db,
            bag,
            models.BagStatusEventType.CREATED.value,
            occurred_at=created_at,
            detail=f"Spawn bag record created for sterilization run {run.run_code}",
        )
        _record_bag_event(
            db,
            bag,
            models.BagStatusEventType.STERILIZED.value,
            occurred_at=process_stage_at,
            detail=f"Sterilization run completed: {run.run_code}",
        )
        _sync_bag_status(bag)
        bags.append(bag)
    db.commit()
    for b in bags:
        db.refresh(b)
    return bags


def create_substrate_bags(
    db: Session,
    pasteurization_run_id: int,
    bag_count: int,
    actual_dry_kg: float | None = None,
) -> list[models.Bag]:
    run = db.get(models.PasteurizationRun, pasteurization_run_id)
    if not run:
        raise ValueError(f"Pasteurization run {pasteurization_run_id} not found")
    existing_bag_count = _count_bags_for_run(db, models.Bag.pasteurization_run_id, pasteurization_run_id)
    _validate_run_capacity(f"Pasteurization run {run.run_code}", run.bag_count, existing_bag_count, bag_count)
    target_dry_kg = None
    if run.mix_lot and run.mix_lot.fill_profile and run.mix_lot.fill_profile.target_dry_kg_per_bag is not None:
        target_dry_kg = float(run.mix_lot.fill_profile.target_dry_kg_per_bag)
    ids = bag_id.generate_internal_bag_ids(db, "SUBSTRATE", bag_count)
    bags = []
    created_at = _now()
    process_stage_at = max(_as_utc(run.unloaded_at) or created_at, created_at)
    for bid in ids:
        bag = models.Bag(
            bag_id=bid,
            bag_type="SUBSTRATE",
            bag_code=None,
            species_id=None,
            pasteurization_run_id=pasteurization_run_id,
            sterilization_run_id=None,
            mix_lot_id=run.mix_lot_id,
            substrate_recipe_version_id=run.substrate_recipe_version_id,
            spawn_recipe_id=None,
            grain_type_id=None,
            target_dry_kg=target_dry_kg,
            actual_dry_kg=actual_dry_kg,
            created_at=created_at,
            labeled_at=None,
            inoculated_at=None,
            status="PASTEURIZED",
        )
        db.add(bag)
        _record_bag_event(
            db,
            bag,
            models.BagStatusEventType.CREATED.value,
            occurred_at=created_at,
            detail=f"Substrate bag record created for pasteurization run {run.run_code}",
        )
        _record_bag_event(
            db,
            bag,
            models.BagStatusEventType.PASTEURIZED.value,
            occurred_at=process_stage_at,
            detail=f"Pasteurization run completed: {run.run_code}",
        )
        _sync_bag_status(bag)
        bags.append(bag)
    db.commit()
    for b in bags:
        db.refresh(b)
    return bags


def get_bag(db: Session, bag_ref: str) -> models.Bag | None:
    return _resolve_bag(db, bag_ref)


def list_bags(
    db: Session,
    bag_type: str | None = None,
    bag_ref_contains: str | None = None,
    species_id: int | None = None,
    pasteurization_run_id: int | None = None,
    sterilization_run_id: int | None = None,
    status: str | None = None,
    limit: int = 500,
):
    stmt = select(models.Bag)
    if bag_type:
        stmt = stmt.where(models.Bag.bag_type == bag_type)
    if bag_ref_contains:
        match = f"%{bag_ref_contains.strip()}%"
        stmt = stmt.where(func.coalesce(models.Bag.bag_code, models.Bag.bag_id).ilike(match))
    if species_id is not None:
        stmt = stmt.where(models.Bag.species_id == species_id)
    if pasteurization_run_id is not None:
        stmt = stmt.where(models.Bag.pasteurization_run_id == pasteurization_run_id)
    if sterilization_run_id is not None:
        stmt = stmt.where(models.Bag.sterilization_run_id == sterilization_run_id)
    if status:
        stmt = stmt.where(models.Bag.status == status)
    stmt = stmt.options(*_bag_lineage_options()).order_by(models.Bag.created_at.desc()).limit(max(1, min(limit, 1000)))
    bags = db.execute(stmt).unique().scalars().all()
    return [_bag_payload(bag) for bag in bags]


def get_bag_detail(db: Session, bag_ref: str) -> dict | None:
    bag = _resolve_bag(db, bag_ref)
    if not bag:
        return None
    bag = db.execute(
        select(models.Bag)
        .options(*_bag_lineage_options())
        .where(models.Bag.bag_id == bag.bag_id)
    ).unique().scalar_one_or_none()
    if not bag:
        return None

    child_rows: list[dict] = []
    child_summary = None
    if bag.bag_type == "SPAWN":
        descendants = _build_descendant_bags(db, [bag.bag_id])
        child_rows = [_build_lineage_row(child_bag, generation) for child_bag, generation in descendants]
        child_summary = _summarize_bags([child_bag for child_bag, _ in descendants])
    status_events = [_build_status_event_row(event) for event in list_bag_status_events(db, bag.bag_id)]

    return {
        **_bag_payload(bag),
        "status_events": status_events,
        "harvest_events": bag.harvest_events,
        "child_bags": child_rows,
        "child_summary": child_summary,
    }


def update_bag_incubation_start(db: Session, bag_ref: str) -> models.Bag | None:
    bag = _resolve_bag(db, bag_ref)
    if not bag:
        return None
    snapshot = _bag_history_snapshot(bag)
    if snapshot["disposed_at"]:
        raise ValueError("Disposed bags cannot enter incubation")
    if not snapshot["inoculated_at"]:
        raise ValueError("Bag must be inoculated before incubation can start")
    if snapshot["incubation_start_at"] is None:
        bag.incubation_start_at = _now()
        _record_bag_event(
            db,
            bag,
            models.BagStatusEventType.INCUBATION_STARTED.value,
            occurred_at=bag.incubation_start_at,
        )
    _sync_bag_status(bag)
    db.commit()
    db.refresh(bag)
    return bag


def update_bag_ready(db: Session, bag_ref: str) -> models.Bag | None:
    bag = _resolve_bag(db, bag_ref)
    if not bag:
        return None
    snapshot = _bag_history_snapshot(bag)
    if snapshot["disposed_at"]:
        raise ValueError("Disposed bags cannot be marked ready")
    if not snapshot["incubation_start_at"]:
        raise ValueError("Bag must enter incubation before it can be marked ready")
    if snapshot["ready_at"] is None:
        bag.ready_at = _now()
        _record_bag_event(
            db,
            bag,
            models.BagStatusEventType.READY.value,
            occurred_at=bag.ready_at,
        )
    _sync_bag_status(bag)
    db.commit()
    db.refresh(bag)
    return bag


def update_bag_fruiting_start(db: Session, bag_ref: str) -> models.Bag | None:
    bag = _resolve_bag(db, bag_ref)
    if not bag:
        return None
    if bag.bag_type != "SUBSTRATE":
        raise ValueError("Only substrate bags can be moved to fruiting")
    snapshot = _bag_history_snapshot(bag)
    if snapshot["disposed_at"]:
        raise ValueError("Disposed bags cannot be moved to fruiting")
    if not snapshot["ready_at"]:
        raise ValueError("Only ready substrate bags can be moved to fruiting")
    if snapshot["fruiting_start_at"] is None:
        bag.fruiting_start_at = _now()
        _record_bag_event(
            db,
            bag,
            models.BagStatusEventType.FRUITING_STARTED.value,
            occurred_at=bag.fruiting_start_at,
        )
    _sync_bag_status(bag)
    db.commit()
    db.refresh(bag)
    return bag


def update_bag_disposal(db: Session, bag_ref: str, disposal_reason: str) -> models.Bag | None:
    bag = _resolve_bag(db, bag_ref)
    if not bag:
        return None
    snapshot = _bag_history_snapshot(bag)
    if snapshot["disposed_at"]:
        raise ValueError("Bag has already been disposed")
    if disposal_reason == "FINAL_HARVEST":
        if bag.bag_type != "SUBSTRATE":
            raise ValueError("Only substrate bags can be disposed as FINAL_HARVEST")
        if bag.total_harvest_kg <= 0:
            raise ValueError("Final harvest disposal requires at least one recorded harvest")
    bag.disposed_at = _now()
    bag.disposal_reason = disposal_reason
    _record_bag_event(
        db,
        bag,
        models.BagStatusEventType.DISPOSED.value,
        occurred_at=bag.disposed_at,
        detail=f"Reason: {disposal_reason}",
    )
    _sync_bag_status(bag)
    db.commit()
    db.refresh(bag)
    return bag


def update_bag_actual_dry_weight(db: Session, bag_ref: str, actual_dry_kg: float | None) -> models.Bag | None:
    bag = _resolve_bag(db, bag_ref)
    if not bag:
        return None
    if bag.bag_type != "SUBSTRATE":
        raise ValueError("Only substrate bags can store dry-weight reporting data")
    bag.actual_dry_kg = actual_dry_kg
    db.commit()
    db.refresh(bag)
    return bag


def inoculate_spawn_bags(
    db: Session,
    sterilization_run_id: int,
    bag_count: int,
    source_type: str,
    liquid_culture_id: int | None = None,
    donor_spawn_bag_ref: str | None = None,
    inoculated_at=None,
    notes: str | None = None,
):
    run = db.get(models.SterilizationRun, sterilization_run_id)
    if not run:
        raise LookupError("Sterilization run not found")

    bags = _get_unlabeled_bags_for_run(
        db,
        bag_type="SPAWN",
        run_column=models.Bag.sterilization_run_id,
        run_id=sterilization_run_id,
        bag_count=bag_count,
    )

    source_spawn_bag = None
    source_liquid_culture = None
    if source_type == models.InoculationSourceType.LIQUID_CULTURE.value:
        if liquid_culture_id is None:
            raise ValueError("Liquid culture is required for liquid-culture spawn inoculation")
        source_liquid_culture = db.get(models.LiquidCulture, liquid_culture_id)
        if not source_liquid_culture:
            raise LookupError("Liquid culture not found")
        if not source_liquid_culture.is_active:
            raise ValueError("Liquid culture must be active before it can be used")
        species_id = source_liquid_culture.species_id
    elif source_type == models.InoculationSourceType.SPAWN_BAG.value:
        if not donor_spawn_bag_ref:
            raise ValueError("Donor spawn bag is required for spawn-to-spawn inoculation")
        source_spawn_bag = _resolve_spawn_source(db, donor_spawn_bag_ref)
        species_id = source_spawn_bag.species_id
    else:
        raise ValueError("Unsupported source_type")

    performed_at = inoculated_at or _now()
    inoculation_detail = (
        f"Inoculated from liquid culture {source_liquid_culture.culture_code}"
        if source_liquid_culture is not None
        else f"Inoculated from spawn bag {source_spawn_bag.bag_ref}"
    )
    bag_codes = bag_id.generate_spawn_bag_ids(db, sterilization_run_id, species_id, len(bags))
    batch = models.InoculationBatch(
        source_type=source_type,
        source_spawn_bag_id=source_spawn_bag.bag_id if source_spawn_bag else None,
        source_liquid_culture_id=(
            source_liquid_culture.liquid_culture_id if source_liquid_culture is not None else None
        ),
        species_id=species_id,
        inoculated_at=performed_at,
        notes=notes,
    )
    db.add(batch)

    for bag, bag_code in zip(bags, bag_codes):
        should_record_label_assignment = bag.bag_code is None or bag.labeled_at is None
        bag.species_id = species_id
        bag.parent_spawn_bag_id = source_spawn_bag.bag_id if source_spawn_bag else None
        bag.source_liquid_culture_id = (
            source_liquid_culture.liquid_culture_id if source_liquid_culture is not None else None
        )
        bag.bag_code = bag_code
        bag.labeled_at = performed_at
        bag.inoculated_at = performed_at
        if should_record_label_assignment:
            _record_bag_event(
                db,
                bag,
                models.BagStatusEventType.BAG_CODE_ASSIGNED.value,
                occurred_at=performed_at,
                detail=f"Printable code assigned: {bag_code}",
            )
        _record_bag_event(
            db,
            bag,
            models.BagStatusEventType.INOCULATED.value,
            occurred_at=performed_at,
            detail=inoculation_detail,
            notes=notes,
        )
        _sync_bag_status(bag)
        db.add(models.InoculationBatchTarget(inoculation_batch=batch, bag=bag))

    if source_spawn_bag is not None:
        source_spawn_bag.consumed_at = performed_at
        _record_bag_event(
            db,
            source_spawn_bag,
            models.BagStatusEventType.CONSUMED.value,
            occurred_at=performed_at,
            detail="Used to inoculate spawn bags",
            notes=notes,
        )
        _sync_bag_status(source_spawn_bag)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    for bag in bags:
        db.refresh(bag)
    return bags


def _create_substrate_inoculations_for_bags(
    db: Session,
    substrate_bags: list[models.Bag],
    spawn_bag_ref: str,
    inoculated_at=None,
    notes: str | None = None,
):
    if not substrate_bags:
        raise ValueError("At least one substrate bag is required")

    spawn = _resolve_spawn_source(db, spawn_bag_ref)

    pasteurization_run_id = substrate_bags[0].pasteurization_run_id
    if pasteurization_run_id is None:
        raise ValueError("Substrate bags must belong to a pasteurization run")

    for bag in substrate_bags:
        bag_snapshot = _bag_history_snapshot(bag)
        if bag.bag_type != "SUBSTRATE":
            raise ValueError("Substrate bag must be SUBSTRATE type")
        if bag_snapshot["disposed_at"]:
            raise ValueError("Disposed substrate bags cannot be inoculated")
        if bag.inoculation is not None:
            raise ValueError(f"Substrate bag already inoculated: {bag.bag_ref}")
        if bag.pasteurization_run_id != pasteurization_run_id:
            raise ValueError("All substrate bags in one inoculation batch must come from the same pasteurization run")

    performed_at = inoculated_at or _now()
    inoculation_detail = f"Inoculated from spawn bag {spawn.bag_ref}"
    bag_codes = bag_id.generate_substrate_bag_ids(db, pasteurization_run_id, spawn.species_id, len(substrate_bags))
    batch = models.InoculationBatch(
        source_type=models.InoculationSourceType.SPAWN_BAG.value,
        source_spawn_bag_id=spawn.bag_id,
        source_liquid_culture_id=None,
        species_id=spawn.species_id,
        inoculated_at=performed_at,
        notes=notes,
    )
    db.add(batch)
    inoculations: list[models.Inoculation] = []

    for bag, bag_code in zip(substrate_bags, bag_codes):
        should_record_label_assignment = bag.bag_code is None or bag.labeled_at is None
        inoc = models.Inoculation(
            substrate_bag_id=bag.bag_id,
            spawn_bag_id=spawn.bag_id,
            inoculated_at=performed_at,
            notes=notes,
        )
        db.add(inoc)
        bag.parent_spawn_bag_id = spawn.bag_id
        bag.source_liquid_culture_id = None
        bag.species_id = spawn.species_id
        bag.bag_code = bag.bag_code or bag_code
        bag.labeled_at = bag.labeled_at or performed_at
        bag.inoculated_at = performed_at
        if should_record_label_assignment:
            _record_bag_event(
                db,
                bag,
                models.BagStatusEventType.BAG_CODE_ASSIGNED.value,
                occurred_at=performed_at,
                detail=f"Printable code assigned: {bag.bag_code}",
            )
        _record_bag_event(
            db,
            bag,
            models.BagStatusEventType.INOCULATED.value,
            occurred_at=performed_at,
            detail=inoculation_detail,
            notes=notes,
        )
        _sync_bag_status(bag)
        inoculations.append(inoc)
        db.add(models.InoculationBatchTarget(inoculation_batch=batch, bag=bag))

    spawn.consumed_at = performed_at
    _record_bag_event(
        db,
        spawn,
        models.BagStatusEventType.CONSUMED.value,
        occurred_at=performed_at,
        detail="Used to inoculate substrate bags",
        notes=notes,
    )
    _sync_bag_status(spawn)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    for bag in substrate_bags:
        db.refresh(bag)
    return substrate_bags


def create_inoculation_batch(
    db: Session,
    pasteurization_run_id: int,
    bag_count: int,
    spawn_bag_id: str,
    inoculated_at=None,
    notes: str | None = None,
):
    substrate_bags = _get_unlabeled_bags_for_run(
        db,
        bag_type="SUBSTRATE",
        run_column=models.Bag.pasteurization_run_id,
        run_id=pasteurization_run_id,
        bag_count=bag_count,
    )
    return _create_substrate_inoculations_for_bags(
        db,
        substrate_bags,
        spawn_bag_ref=spawn_bag_id,
        inoculated_at=inoculated_at,
        notes=notes,
    )


def create_inoculation(
    db: Session,
    substrate_bag_id: str,
    spawn_bag_id: str,
    inoculated_at=None,
    notes: str | None = None,
):
    substrate_bag = _resolve_bag(db, substrate_bag_id)
    if not substrate_bag:
        raise LookupError("Substrate bag not found")
    inoculated_bag = _create_substrate_inoculations_for_bags(
        db,
        [substrate_bag],
        spawn_bag_ref=spawn_bag_id,
        inoculated_at=inoculated_at,
        notes=notes,
    )[0]
    inoculation = get_inoculation_for_substrate_bag(db, inoculated_bag.bag_id)
    if inoculation is None:
        raise LookupError("Inoculation not found after creation")
    return inoculation


def get_inoculation_for_substrate_bag(db: Session, substrate_bag_ref: str):
    bag = _resolve_bag(db, substrate_bag_ref)
    if not bag:
        return None
    return db.execute(
        select(models.Inoculation).where(models.Inoculation.substrate_bag_id == bag.bag_id)
    ).scalar_one_or_none()


def list_substrate_bags_inoculated_by(db: Session, spawn_bag_ref: str):
    spawn = _resolve_bag(db, spawn_bag_ref)
    if not spawn:
        return []
    inocs = db.execute(
        select(models.Inoculation).where(models.Inoculation.spawn_bag_id == spawn.bag_id)
    ).scalars().all()
    ids = [i.substrate_bag_id for i in inocs]
    if not ids:
        return []
    return db.execute(
        select(models.Bag).where(models.Bag.bag_id.in_(ids)).order_by(models.Bag.bag_id.asc())
    ).scalars().all()


def create_harvest_event(db: Session, bag_ref: str, flush_number: int, fresh_weight_kg: float, harvested_at=None, notes=None):
    bag = _resolve_bag(db, bag_ref)
    if not bag:
        raise LookupError("Bag not found")
    if bag.bag_type != "SUBSTRATE":
        raise ValueError("Harvest events only for substrate bags")
    snapshot = _bag_history_snapshot(bag)
    if snapshot["disposed_at"]:
        raise ValueError("Disposed bags cannot be harvested")
    if not snapshot["fruiting_start_at"]:
        raise ValueError("Bag must enter fruiting before harvest")
    ev = models.HarvestEvent(
        bag=bag,
        flush_number=flush_number,
        fresh_weight_kg=fresh_weight_kg,
        harvested_at=harvested_at or _now(),
        notes=notes,
    )
    db.add(ev)
    try:
        db.flush()
        _record_bag_event(
            db,
            bag,
            models.BagStatusEventType.HARVEST_RECORDED.value,
            occurred_at=ev.harvested_at,
            detail=_format_harvest_event_detail(flush_number, fresh_weight_kg),
            notes=notes,
        )
        _sync_bag_status(bag)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(ev)
    return ev


def list_harvest_events_for_bag(db: Session, bag_id: str):
    bag = _resolve_bag(db, bag_id)
    if not bag:
        return []
    return db.execute(
        select(models.HarvestEvent)
        .where(models.HarvestEvent.bag_id == bag.bag_id)
        .order_by(models.HarvestEvent.flush_number.asc())
    ).scalars().all()


def get_bag_total_harvest_kg(db: Session, bag_id: str) -> float:
    bag = _resolve_bag(db, bag_id)
    if not bag:
        return 0.0
    row = db.execute(
        select(func.coalesce(func.sum(models.HarvestEvent.fresh_weight_kg), 0))
        .where(models.HarvestEvent.bag_id == bag.bag_id)
    ).scalar_one()
    return float(row)
