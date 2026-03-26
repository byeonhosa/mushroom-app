from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

from . import models
from . import bag_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _derive_bag_status_from_caches(bag: models.Bag) -> str:
    if bag.disposed_at:
        return "CONTAMINATED" if bag.disposal_reason == "CONTAMINATION" else "DISPOSED"

    if bag.bag_type == "SPAWN":
        if bag.consumed_at:
            return "CONSUMED"
        if bag.ready_at:
            return "READY"
        if bag.incubation_start_at:
            return "INCUBATING"
        if bag.inoculated_at:
            return "INOCULATED"
        return "STERILIZED"

    harvest_count = len(bag.harvest_events)
    if harvest_count >= 2:
        return "FLUSH_2_COMPLETE"
    if harvest_count >= 1:
        return "FLUSH_1_COMPLETE"
    if bag.fruiting_start_at:
        return "FRUITING"
    if bag.ready_at:
        return "READY"
    if bag.incubation_start_at:
        return "INCUBATING"
    if bag.inoculated_at:
        return "INOCULATED"
        return "PASTEURIZED"


def _event_time_by_type(bag: models.Bag) -> dict[str, datetime]:
    event_times: dict[str, datetime] = {}
    for event in sorted(
        bag.status_events,
        key=lambda row: (_as_utc(row.occurred_at) or _now(), row.bag_status_event_id or 0),
    ):
        event_times[event.event_type] = _as_utc(event.occurred_at) or _now()
    return event_times


def _derive_bag_status_from_history(bag: models.Bag, event_times: dict[str, datetime]) -> str:
    if event_times.get(models.BagStatusEventType.DISPOSED.value) or bag.disposed_at:
        return "CONTAMINATED" if bag.disposal_reason == "CONTAMINATION" else "DISPOSED"

    if bag.bag_type == "SPAWN":
        if event_times.get(models.BagStatusEventType.CONSUMED.value) or bag.consumed_at:
            return "CONSUMED"
        if event_times.get(models.BagStatusEventType.READY.value) or bag.ready_at:
            return "READY"
        if event_times.get(models.BagStatusEventType.INCUBATION_STARTED.value) or bag.incubation_start_at:
            return "INCUBATING"
        if event_times.get(models.BagStatusEventType.INOCULATED.value) or bag.inoculated_at:
            return "INOCULATED"
        if event_times.get(models.BagStatusEventType.STERILIZED.value):
            return "STERILIZED"
        return "CREATED"

    harvest_count = len(bag.harvest_events)
    if harvest_count >= 2:
        return "FLUSH_2_COMPLETE"
    if harvest_count >= 1:
        return "FLUSH_1_COMPLETE"
    if event_times.get(models.BagStatusEventType.FRUITING_STARTED.value) or bag.fruiting_start_at:
        return "FRUITING"
    if event_times.get(models.BagStatusEventType.READY.value) or bag.ready_at:
        return "READY"
    if event_times.get(models.BagStatusEventType.INCUBATION_STARTED.value) or bag.incubation_start_at:
        return "INCUBATING"
    if event_times.get(models.BagStatusEventType.INOCULATED.value) or bag.inoculated_at:
        return "INOCULATED"
    if event_times.get(models.BagStatusEventType.PASTEURIZED.value):
        return "PASTEURIZED"
    return "CREATED"


def _bag_history_snapshot(bag: models.Bag) -> dict:
    event_times = _event_time_by_type(bag)
    if event_times:
        status = _derive_bag_status_from_history(bag, event_times)
    else:
        status = _derive_bag_status_from_caches(bag)

    return {
        "created_at": event_times.get(models.BagStatusEventType.CREATED.value, _as_utc(bag.created_at)),
        "labeled_at": event_times.get(models.BagStatusEventType.BAG_CODE_ASSIGNED.value, _as_utc(bag.labeled_at)),
        "inoculated_at": event_times.get(models.BagStatusEventType.INOCULATED.value, _as_utc(bag.inoculated_at)),
        "incubation_start_at": event_times.get(models.BagStatusEventType.INCUBATION_STARTED.value, _as_utc(bag.incubation_start_at)),
        "ready_at": event_times.get(models.BagStatusEventType.READY.value, _as_utc(bag.ready_at)),
        "fruiting_start_at": event_times.get(models.BagStatusEventType.FRUITING_STARTED.value, _as_utc(bag.fruiting_start_at)),
        "disposed_at": event_times.get(models.BagStatusEventType.DISPOSED.value, _as_utc(bag.disposed_at)),
        "consumed_at": event_times.get(models.BagStatusEventType.CONSUMED.value, _as_utc(bag.consumed_at)),
        "status": status,
    }


def _sync_bag_status(bag: models.Bag) -> str:
    bag.status = _bag_history_snapshot(bag)["status"]
    return bag.status


def _record_bag_event(
    db: Session,
    bag: models.Bag,
    event_type: str,
    *,
    occurred_at: datetime | None = None,
    detail: str | None = None,
    notes: str | None = None,
) -> models.BagStatusEvent:
    event = models.BagStatusEvent(
        bag=bag,
        event_type=event_type,
        occurred_at=_as_utc(occurred_at) or _now(),
        detail=detail,
        notes=notes,
    )
    db.add(event)
    return event


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


def list_bag_status_events(db: Session, bag_ref: str):
    bag = _resolve_bag(db, bag_ref)
    if not bag:
        return []
    return db.execute(
        select(models.BagStatusEvent)
        .where(models.BagStatusEvent.bag_id == bag.bag_id)
        .order_by(models.BagStatusEvent.occurred_at.asc(), models.BagStatusEvent.bag_status_event_id.asc())
    ).scalars().all()


def _resolve_bag(db: Session, bag_ref: str) -> models.Bag | None:
    bag = db.get(models.Bag, bag_ref)
    if bag:
        return bag
    return db.execute(select(models.Bag).where(models.Bag.bag_code == bag_ref)).scalar_one_or_none()


def _bag_lineage_options():
    return (
        joinedload(models.Bag.species),
        joinedload(models.Bag.pasteurization_run),
        joinedload(models.Bag.sterilization_run),
        joinedload(models.Bag.parent_spawn_bag).joinedload(models.Bag.sterilization_run),
        joinedload(models.Bag.source_liquid_culture),
        joinedload(models.Bag.harvest_events),
        joinedload(models.Bag.status_events),
    )


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


def _build_descendant_bags(db: Session, root_bag_ids: list[str]) -> list[tuple[models.Bag, int]]:
    descendants: list[tuple[models.Bag, int]] = []
    seen = set(root_bag_ids)
    frontier = list(root_bag_ids)
    generation = 1

    while frontier:
        rows = db.execute(
            select(models.Bag)
            .options(*_bag_lineage_options())
            .where(models.Bag.parent_spawn_bag_id.in_(frontier))
            .order_by(models.Bag.created_at.asc(), models.Bag.bag_id.asc())
        ).unique().scalars().all()
        if not rows:
            break

        next_frontier: list[str] = []
        for row in rows:
            if row.bag_id in seen:
                continue
            seen.add(row.bag_id)
            descendants.append((row, generation))
            if row.bag_type == "SPAWN":
                next_frontier.append(row.bag_id)
        frontier = next_frontier
        generation += 1

    return descendants


def calculate_bio_efficiency(
    total_harvest_kg: float,
    *,
    actual_dry_kg: float | None = None,
    target_dry_kg: float | None = None,
) -> tuple[float | None, float | None, str | None]:
    if actual_dry_kg is not None and actual_dry_kg > 0:
        return total_harvest_kg / actual_dry_kg, actual_dry_kg, "ACTUAL"
    if target_dry_kg is not None and target_dry_kg > 0:
        return total_harvest_kg / target_dry_kg, target_dry_kg, "TARGET"
    return None, None, None


def _is_contaminated(bag: models.Bag) -> bool:
    return bag.disposal_reason == "CONTAMINATION"


def _build_group_summary(entries: list[tuple[str, str, bool]]) -> list[dict]:
    groups: dict[str, dict] = {}
    for key, label, contaminated in entries:
        group = groups.setdefault(
            key,
            {
                "key": key,
                "label": label,
                "total_bags": 0,
                "contaminated_bags": 0,
            },
        )
        group["total_bags"] += 1
        if contaminated:
            group["contaminated_bags"] += 1

    results = []
    for group in groups.values():
        total_bags = group["total_bags"]
        contaminated_bags = group["contaminated_bags"]
        results.append(
            {
                **group,
                "contamination_rate": contaminated_bags / total_bags if total_bags else 0.0,
            }
        )
    return sorted(results, key=lambda row: (-row["contaminated_bags"], row["label"]))


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


def _root_liquid_culture_for_bag(
    bag: models.Bag,
    bag_index: dict[str, models.Bag],
    memo: dict[str, tuple[int | None, str | None]],
    visiting: set[str] | None = None,
) -> tuple[int | None, str | None]:
    if bag.bag_id in memo:
        return memo[bag.bag_id]

    if visiting is None:
        visiting = set()
    if bag.bag_id in visiting:
        return (None, None)

    visiting.add(bag.bag_id)
    result: tuple[int | None, str | None]
    if bag.source_liquid_culture_id is not None:
        result = (
            bag.source_liquid_culture_id,
            bag.source_liquid_culture.culture_code if bag.source_liquid_culture else None,
        )
    elif bag.parent_spawn_bag_id and bag.parent_spawn_bag_id in bag_index:
        result = _root_liquid_culture_for_bag(bag_index[bag.parent_spawn_bag_id], bag_index, memo, visiting)
    else:
        result = (None, None)
    visiting.remove(bag.bag_id)
    memo[bag.bag_id] = result
    return result


def _spawn_generation_for_bag(
    bag: models.Bag,
    bag_index: dict[str, models.Bag],
    memo: dict[str, int | None],
    visiting: set[str] | None = None,
) -> int | None:
    if bag.bag_id in memo:
        return memo[bag.bag_id]

    if visiting is None:
        visiting = set()
    if bag.bag_id in visiting:
        return None

    visiting.add(bag.bag_id)
    generation: int | None
    if bag.bag_type == "SPAWN":
        if bag.source_liquid_culture_id is not None:
            generation = 1
        elif bag.parent_spawn_bag_id and bag.parent_spawn_bag_id in bag_index:
            parent_generation = _spawn_generation_for_bag(bag_index[bag.parent_spawn_bag_id], bag_index, memo, visiting)
            generation = parent_generation + 1 if parent_generation is not None else None
        else:
            generation = None
    else:
        if bag.parent_spawn_bag_id and bag.parent_spawn_bag_id in bag_index:
            generation = _spawn_generation_for_bag(bag_index[bag.parent_spawn_bag_id], bag_index, memo, visiting)
        elif bag.source_liquid_culture_id is not None:
            generation = 1
        else:
            generation = None
    visiting.remove(bag.bag_id)
    memo[bag.bag_id] = generation
    return generation


def _build_lineage_metadata(
    bag: models.Bag,
    bag_index: dict[str, models.Bag],
    liquid_culture_memo: dict[str, tuple[int | None, str | None]],
    generation_memo: dict[str, int | None],
) -> dict:
    source_liquid_culture_id, source_liquid_culture_code = _root_liquid_culture_for_bag(
        bag,
        bag_index,
        liquid_culture_memo,
    )
    return {
        "source_liquid_culture_id": source_liquid_culture_id,
        "source_liquid_culture_code": source_liquid_culture_code,
        "spawn_generation": _spawn_generation_for_bag(bag, bag_index, generation_memo),
    }


def _build_data_quality_issues(bags: list[models.Bag]) -> list[dict]:
    snapshots = {bag.bag_id: _bag_history_snapshot(bag) for bag in bags}
    issues = [
        (
            "INOCULATED_SPAWN_MISSING_SOURCE",
            "Inoculated spawn bags missing an inoculation source",
            lambda bag, snapshot: bag.bag_type == "SPAWN"
            and snapshot["inoculated_at"] is not None
            and bag.source_liquid_culture_id is None
            and bag.parent_spawn_bag_id is None,
        ),
        (
            "INOCULATED_SUBSTRATE_MISSING_PARENT",
            "Inoculated substrate bags missing a parent spawn bag",
            lambda bag, snapshot: bag.bag_type == "SUBSTRATE"
            and snapshot["inoculated_at"] is not None
            and bag.parent_spawn_bag_id is None,
        ),
        (
            "INOCULATED_BAG_MISSING_SPECIES",
            "Inoculated bags missing species assignment",
            lambda bag, snapshot: snapshot["inoculated_at"] is not None and bag.species_id is None,
        ),
        (
            "READY_WITHOUT_INCUBATION",
            "Bags marked ready without an incubation start",
            lambda bag, snapshot: snapshot["ready_at"] is not None and snapshot["incubation_start_at"] is None,
        ),
        (
            "FRUITING_WITHOUT_READY",
            "Substrate bags moved to fruiting without a ready timestamp",
            lambda bag, snapshot: bag.bag_type == "SUBSTRATE"
            and snapshot["fruiting_start_at"] is not None
            and snapshot["ready_at"] is None,
        ),
        (
            "FINAL_HARVEST_WITHOUT_HARVEST",
            "Bags disposed as final harvest without any recorded harvest weight",
            lambda bag, snapshot: bag.disposal_reason == "FINAL_HARVEST" and bag.total_harvest_kg <= 0,
        ),
        (
            "FINAL_HARVEST_ON_NON_SUBSTRATE",
            "Non-substrate bags disposed as final harvest",
            lambda bag, snapshot: bag.disposal_reason == "FINAL_HARVEST" and bag.bag_type != "SUBSTRATE",
        ),
    ]

    rows: list[dict] = []
    for code, label, predicate in issues:
        matching = [bag.bag_ref for bag in bags if predicate(bag, snapshots[bag.bag_id])]
        if matching:
            rows.append(
                {
                    "code": code,
                    "label": label,
                    "count": len(matching),
                    "bag_refs": matching[:5],
                }
            )
    return rows


def _bag_payload(bag: models.Bag) -> dict:
    snapshot = _bag_history_snapshot(bag)
    bio_efficiency, dry_weight_kg, dry_weight_source = calculate_bio_efficiency(
        bag.total_harvest_kg,
        actual_dry_kg=float(bag.actual_dry_kg) if bag.actual_dry_kg is not None else None,
        target_dry_kg=float(bag.target_dry_kg) if bag.target_dry_kg is not None else None,
    )
    return {
        "bag_id": bag.bag_id,
        "bag_code": bag.bag_code,
        "bag_ref": bag.bag_ref,
        "bag_type": bag.bag_type,
        "species_id": bag.species_id,
        "pasteurization_run_id": bag.pasteurization_run_id,
        "sterilization_run_id": bag.sterilization_run_id,
        "mix_lot_id": bag.mix_lot_id,
        "substrate_recipe_version_id": bag.substrate_recipe_version_id,
        "spawn_recipe_id": bag.spawn_recipe_id,
        "grain_type_id": bag.grain_type_id,
        "parent_spawn_bag_id": bag.parent_spawn_bag_id,
        "parent_spawn_bag_ref": bag.parent_spawn_bag_ref,
        "source_spawn_bag_id": bag.source_spawn_bag_id,
        "source_spawn_bag_ref": bag.source_spawn_bag_ref,
        "source_liquid_culture_id": bag.source_liquid_culture_id,
        "source_liquid_culture_code": bag.source_liquid_culture_code,
        "inoculation_source_type": bag.inoculation_source_type,
        "target_dry_kg": float(bag.target_dry_kg) if bag.target_dry_kg is not None else None,
        "actual_dry_kg": float(bag.actual_dry_kg) if bag.actual_dry_kg is not None else None,
        "dry_weight_kg": dry_weight_kg,
        "dry_weight_source": dry_weight_source,
        "bio_efficiency": bio_efficiency,
        "created_at": snapshot["created_at"],
        "labeled_at": snapshot["labeled_at"],
        "inoculated_at": snapshot["inoculated_at"],
        "incubation_start_at": snapshot["incubation_start_at"],
        "ready_at": snapshot["ready_at"],
        "fruiting_start_at": snapshot["fruiting_start_at"],
        "disposed_at": snapshot["disposed_at"],
        "disposal_reason": bag.disposal_reason,
        "consumed_at": snapshot["consumed_at"],
        "status": snapshot["status"],
        "notes": bag.notes,
    }


def _build_substrate_metrics_row(bag: models.Bag, lineage_metadata: dict | None = None) -> dict:
    snapshot = _bag_history_snapshot(bag)
    source_sterilization_run = bag.parent_spawn_bag.sterilization_run if bag.parent_spawn_bag else None
    bio_efficiency, dry_weight_kg, dry_weight_source = calculate_bio_efficiency(
        bag.total_harvest_kg,
        actual_dry_kg=float(bag.actual_dry_kg) if bag.actual_dry_kg is not None else None,
        target_dry_kg=float(bag.target_dry_kg) if bag.target_dry_kg is not None else None,
    )
    if lineage_metadata is None:
        lineage_metadata = {
            "source_liquid_culture_id": bag.source_liquid_culture_id,
            "source_liquid_culture_code": bag.source_liquid_culture_code,
            "spawn_generation": 1 if bag.source_liquid_culture_id is not None else None,
        }
    return {
        "bag_id": bag.bag_id,
        "bag_code": bag.bag_code,
        "bag_ref": bag.bag_ref,
        "status": snapshot["status"],
        "disposal_reason": bag.disposal_reason,
        "species_id": bag.species_id,
        "species_code": bag.species.code if bag.species else None,
        "species_name": bag.species.name if bag.species else None,
        "pasteurization_run_id": bag.pasteurization_run_id,
        "pasteurization_run_code": bag.pasteurization_run.run_code if bag.pasteurization_run else None,
        "parent_spawn_bag_id": bag.parent_spawn_bag_id,
        "parent_spawn_bag_ref": bag.parent_spawn_bag_ref,
        "source_liquid_culture_id": lineage_metadata["source_liquid_culture_id"],
        "source_liquid_culture_code": lineage_metadata["source_liquid_culture_code"],
        "spawn_generation": lineage_metadata["spawn_generation"],
        "source_sterilization_run_id": (
            source_sterilization_run.sterilization_run_id if source_sterilization_run is not None else None
        ),
        "source_sterilization_run_code": source_sterilization_run.run_code if source_sterilization_run else None,
        "target_dry_kg": float(bag.target_dry_kg) if bag.target_dry_kg is not None else None,
        "actual_dry_kg": float(bag.actual_dry_kg) if bag.actual_dry_kg is not None else None,
        "dry_weight_kg": dry_weight_kg,
        "dry_weight_source": dry_weight_source,
        "total_harvest_kg": bag.total_harvest_kg,
        "bio_efficiency": bio_efficiency,
        "contaminated": _is_contaminated(bag),
    }


def _build_lineage_row(bag: models.Bag, generation: int) -> dict:
    snapshot = _bag_history_snapshot(bag)
    source_sterilization_run = bag.parent_spawn_bag.sterilization_run if bag.parent_spawn_bag else None
    bio_efficiency, dry_weight_kg, dry_weight_source = calculate_bio_efficiency(
        bag.total_harvest_kg,
        actual_dry_kg=float(bag.actual_dry_kg) if bag.actual_dry_kg is not None else None,
        target_dry_kg=float(bag.target_dry_kg) if bag.target_dry_kg is not None else None,
    )
    return {
        "generation": generation,
        "bag_id": bag.bag_id,
        "bag_code": bag.bag_code,
        "bag_ref": bag.bag_ref,
        "bag_type": bag.bag_type,
        "status": snapshot["status"],
        "disposal_reason": bag.disposal_reason,
        "species_id": bag.species_id,
        "species_code": bag.species.code if bag.species else None,
        "species_name": bag.species.name if bag.species else None,
        "sterilization_run_id": bag.sterilization_run_id,
        "sterilization_run_code": bag.sterilization_run.run_code if bag.sterilization_run else None,
        "pasteurization_run_id": bag.pasteurization_run_id,
        "pasteurization_run_code": bag.pasteurization_run.run_code if bag.pasteurization_run else None,
        "parent_spawn_bag_id": bag.parent_spawn_bag_id,
        "parent_spawn_bag_ref": bag.parent_spawn_bag_ref,
        "source_liquid_culture_id": bag.source_liquid_culture_id,
        "source_liquid_culture_code": bag.source_liquid_culture_code,
        "inoculation_source_type": bag.inoculation_source_type,
        "source_sterilization_run_id": (
            source_sterilization_run.sterilization_run_id if source_sterilization_run is not None else None
        ),
        "source_sterilization_run_code": source_sterilization_run.run_code if source_sterilization_run else None,
        "target_dry_kg": float(bag.target_dry_kg) if bag.target_dry_kg is not None else None,
        "actual_dry_kg": float(bag.actual_dry_kg) if bag.actual_dry_kg is not None else None,
        "dry_weight_kg": dry_weight_kg,
        "dry_weight_source": dry_weight_source,
        "total_harvest_kg": bag.total_harvest_kg,
        "bio_efficiency": bio_efficiency,
        "contaminated": _is_contaminated(bag),
    }


def _summarize_bags(bags: list[models.Bag]) -> dict:
    total_harvest_kg = 0.0
    total_dry_weight_kg = 0.0
    harvested_bags = 0
    snapshots = {bag.bag_id: _bag_history_snapshot(bag) for bag in bags}
    for bag in bags:
        if bag.bag_type == "SUBSTRATE":
            if bag.total_harvest_kg > 0:
                harvested_bags += 1
            total_harvest_kg += bag.total_harvest_kg
            if bag.dry_weight_kg is not None:
                total_dry_weight_kg += bag.dry_weight_kg

    total_bags = len(bags)
    return {
        "total_bags": total_bags,
        "unlabeled_bags": sum(1 for bag in bags if bag.bag_code is None),
        "inoculated_bags": sum(1 for bag in bags if snapshots[bag.bag_id]["inoculated_at"] is not None),
        "ready_bags": sum(1 for bag in bags if snapshots[bag.bag_id]["ready_at"] is not None),
        "fruiting_bags": sum(1 for bag in bags if snapshots[bag.bag_id]["fruiting_start_at"] is not None),
        "contaminated_bags": sum(1 for bag in bags if _is_contaminated(bag)),
        "harvested_bags": harvested_bags,
        "consumed_bags": sum(1 for bag in bags if snapshots[bag.bag_id]["consumed_at"] is not None),
        "total_harvest_kg": total_harvest_kg,
        "total_dry_weight_kg": total_dry_weight_kg,
        "overall_bio_efficiency": total_harvest_kg / total_dry_weight_kg if total_dry_weight_kg > 0 else None,
    }


def _summarize_substrate_metric_rows(rows: list[dict]) -> dict:
    total_bags = len(rows)
    total_harvest_kg = sum(row["total_harvest_kg"] for row in rows)
    total_dry_weight_kg = sum(row["dry_weight_kg"] or 0.0 for row in rows)
    return {
        "total_bags": total_bags,
        "unlabeled_bags": sum(1 for row in rows if row["bag_code"] is None),
        "inoculated_bags": sum(1 for row in rows if row["status"] not in {"PASTEURIZED"}),
        "ready_bags": sum(1 for row in rows if row["status"] in {"READY", "FRUITING", "FLUSH_1_COMPLETE", "FLUSH_2_COMPLETE", "DISPOSED", "CONTAMINATED"}),
        "fruiting_bags": sum(1 for row in rows if row["status"] in {"FRUITING", "FLUSH_1_COMPLETE", "FLUSH_2_COMPLETE"}),
        "contaminated_bags": sum(1 for row in rows if row["contaminated"]),
        "harvested_bags": sum(1 for row in rows if row["total_harvest_kg"] > 0),
        "consumed_bags": 0,
        "total_harvest_kg": total_harvest_kg,
        "total_dry_weight_kg": total_dry_weight_kg,
        "overall_bio_efficiency": total_harvest_kg / total_dry_weight_kg if total_dry_weight_kg > 0 else None,
    }


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


# --- Reference data ---

def list_fill_profiles(db: Session):
    return db.execute(select(models.FillProfile).order_by(models.FillProfile.fill_profile_id)).scalars().all()


def create_fill_profile(db: Session, name: str, dry: float, water: float, notes: str | None):
    fp = models.FillProfile(name=name, target_dry_kg_per_bag=dry, target_water_kg_per_bag=water, notes=notes)
    db.add(fp)
    db.commit()
    db.refresh(fp)
    return fp


def list_substrate_recipe_versions(db: Session):
    return db.execute(
        select(models.SubstrateRecipeVersion).order_by(models.SubstrateRecipeVersion.substrate_recipe_version_id)
    ).scalars().all()


def create_substrate_recipe_version(db: Session, data: dict):
    r = models.SubstrateRecipeVersion(**data)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def list_spawn_recipes(db: Session):
    return db.execute(select(models.SpawnRecipe).order_by(models.SpawnRecipe.spawn_recipe_id)).scalars().all()


def create_spawn_recipe(db: Session, data: dict):
    r = models.SpawnRecipe(**data)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def list_mix_lots(db: Session):
    return db.execute(select(models.MixLot).order_by(models.MixLot.mix_lot_id.desc())).scalars().all()


def create_mix_lot(db: Session, data: dict):
    m = models.MixLot(**data)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def list_species(db: Session, active_only: bool = True):
    stmt = select(models.MushroomSpecies).order_by(models.MushroomSpecies.name.asc(), models.MushroomSpecies.species_id.asc())
    if active_only:
        stmt = stmt.where(models.MushroomSpecies.is_active.is_(True))
    return db.execute(stmt).scalars().all()


def create_species(db: Session, data: dict):
    s = models.MushroomSpecies(**data)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def update_species(db: Session, species_id: int, data: dict):
    s = db.get(models.MushroomSpecies, species_id)
    if not s:
        return None
    for k, v in data.items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s


def list_liquid_cultures(db: Session, active_only: bool = True):
    stmt = (
        select(models.LiquidCulture)
        .options(joinedload(models.LiquidCulture.species))
        .order_by(models.LiquidCulture.culture_code.asc(), models.LiquidCulture.liquid_culture_id.asc())
    )
    if active_only:
        stmt = stmt.where(models.LiquidCulture.is_active.is_(True))
    return db.execute(stmt).scalars().all()


def create_liquid_culture(db: Session, data: dict):
    culture = models.LiquidCulture(**data)
    db.add(culture)
    db.commit()
    db.refresh(culture)
    return culture


def list_grain_types(db: Session):
    return db.execute(
        select(models.GrainType).order_by(models.GrainType.name.asc(), models.GrainType.grain_type_id.asc())
    ).scalars().all()


def create_grain_type(db: Session, data: dict):
    g = models.GrainType(**data)
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


def update_grain_type(db: Session, grain_type_id: int, data: dict):
    g = db.get(models.GrainType, grain_type_id)
    if not g:
        return None
    for k, v in data.items():
        setattr(g, k, v)
    db.commit()
    db.refresh(g)
    return g


def list_ingredients(db: Session):
    return db.execute(
        select(models.Ingredient).order_by(models.Ingredient.name.asc(), models.Ingredient.ingredient_id.asc())
    ).scalars().all()


def create_ingredient(db: Session, data: dict):
    i = models.Ingredient(**data)
    db.add(i)
    db.commit()
    db.refresh(i)
    return i


def update_ingredient(db: Session, ingredient_id: int, data: dict):
    i = db.get(models.Ingredient, ingredient_id)
    if not i:
        return None
    for k, v in data.items():
        setattr(i, k, v)
    db.commit()
    db.refresh(i)
    return i


def list_ingredient_lots(db: Session, ingredient_id: int | None = None):
    stmt = select(models.IngredientLot).order_by(models.IngredientLot.ingredient_lot_id.desc())
    if ingredient_id is not None:
        stmt = stmt.where(models.IngredientLot.ingredient_id == ingredient_id)
    return db.execute(stmt).scalars().all()


def create_ingredient_lot(db: Session, data: dict):
    lot = models.IngredientLot(**data)
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot


# --- Pasteurization runs ---

def create_pasteurization_run(db: Session, data: dict):
    r = models.PasteurizationRun(**data)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def list_pasteurization_runs(db: Session):
    return db.execute(
        select(models.PasteurizationRun).order_by(models.PasteurizationRun.pasteurization_run_id.desc())
    ).scalars().all()


def get_pasteurization_run(db: Session, pasteurization_run_id: int):
    return db.get(models.PasteurizationRun, pasteurization_run_id)


def update_pasteurization_run(db: Session, pasteurization_run_id: int, data: dict):
    r = db.get(models.PasteurizationRun, pasteurization_run_id)
    if not r:
        return None
    for k, v in data.items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return r


# --- Sterilization runs ---

def create_sterilization_run(db: Session, data: dict):
    r = models.SterilizationRun(**data)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def list_sterilization_runs(
    db: Session,
    run_code_contains: str | None = None,
    sort_by: str = "sterilization_run_id",
    sort_order: str = "desc",
):
    stmt = select(models.SterilizationRun)
    if run_code_contains:
        stmt = stmt.where(models.SterilizationRun.run_code.ilike(f"%{run_code_contains}%"))
    sort_col = getattr(models.SterilizationRun, sort_by, models.SterilizationRun.sterilization_run_id)
    stmt = stmt.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())
    return db.execute(stmt).scalars().all()


def get_sterilization_run(db: Session, sterilization_run_id: int):
    return db.get(models.SterilizationRun, sterilization_run_id)


def update_sterilization_run(db: Session, sterilization_run_id: int, data: dict):
    r = db.get(models.SterilizationRun, sterilization_run_id)
    if not r:
        return None
    for k, v in data.items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return r


# --- Bags ---

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


def get_sterilization_run_detail(db: Session, sterilization_run_id: int) -> dict | None:
    run = db.get(models.SterilizationRun, sterilization_run_id)
    if not run:
        return None

    spawn_bags = db.execute(
        select(models.Bag)
        .options(*_bag_lineage_options())
        .where(models.Bag.sterilization_run_id == sterilization_run_id)
        .order_by(models.Bag.created_at.asc(), models.Bag.bag_id.asc())
    ).unique().scalars().all()

    spawn_bag_ids = [bag.bag_id for bag in spawn_bags]
    descendants = _build_descendant_bags(db, spawn_bag_ids) if spawn_bag_ids else []
    downstream_bags = [bag for bag, _ in descendants if bag.bag_type == "SUBSTRATE"]
    downstream_rows = [_build_substrate_metrics_row(bag) for bag in downstream_bags]
    return {
        "sterilization_run_id": run.sterilization_run_id,
        "run_code": run.run_code,
        "spawn_recipe_id": run.spawn_recipe_id,
        "grain_type_id": run.grain_type_id,
        "cycle_start_at": run.cycle_start_at,
        "cycle_end_at": run.cycle_end_at,
        "unloaded_at": run.unloaded_at,
        "bag_count": run.bag_count,
        "temp_c": float(run.temp_c) if run.temp_c is not None else None,
        "psi": float(run.psi) if run.psi is not None else None,
        "hold_minutes": run.hold_minutes,
        "notes": run.notes,
        "bags": [_bag_payload(bag) for bag in spawn_bags],
        "summary": _summarize_bags(spawn_bags),
        "downstream_substrate_bags": downstream_rows,
        "downstream_summary": _summarize_bags(downstream_bags),
    }


def get_pasteurization_run_detail(db: Session, pasteurization_run_id: int) -> dict | None:
    run = db.get(models.PasteurizationRun, pasteurization_run_id)
    if not run:
        return None

    substrate_bags = db.execute(
        select(models.Bag)
        .options(*_bag_lineage_options())
        .where(models.Bag.pasteurization_run_id == pasteurization_run_id)
        .order_by(models.Bag.created_at.asc(), models.Bag.bag_id.asc())
    ).unique().scalars().all()

    bag_rows = [_build_substrate_metrics_row(bag) for bag in substrate_bags]
    return {
        "pasteurization_run_id": run.pasteurization_run_id,
        "run_code": run.run_code,
        "mix_lot_id": run.mix_lot_id,
        "substrate_recipe_version_id": run.substrate_recipe_version_id,
        "steam_start_at": run.steam_start_at,
        "steam_end_at": run.steam_end_at,
        "unloaded_at": run.unloaded_at,
        "bag_count": run.bag_count,
        "notes": run.notes,
        "bags": bag_rows,
        "summary": _summarize_substrate_metric_rows(bag_rows),
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


# --- Inoculations ---

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


# --- Harvest events ---

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


def get_production_report(db: Session) -> dict:
    bags = db.execute(
        select(models.Bag)
        .options(*_bag_lineage_options())
        .order_by(models.Bag.created_at.desc(), models.Bag.bag_id.desc())
    ).unique().scalars().all()

    bag_index = {bag.bag_id: bag for bag in bags}
    liquid_culture_memo: dict[str, tuple[int | None, str | None]] = {}
    generation_memo: dict[str, int | None] = {}

    substrate_rows: list[dict] = []
    contamination_by_bag_type_entries: list[tuple[str, str, bool]] = []
    contamination_by_species_entries: list[tuple[str, str, bool]] = []
    contamination_by_liquid_culture_entries: list[tuple[str, str, bool]] = []
    contamination_by_inoculation_source_type_entries: list[tuple[str, str, bool]] = []
    contamination_by_spawn_generation_entries: list[tuple[str, str, bool]] = []
    contamination_by_source_sterilization_entries: list[tuple[str, str, bool]] = []
    contamination_by_pasteurization_entries: list[tuple[str, str, bool]] = []
    contamination_by_parent_spawn_entries: list[tuple[str, str, bool]] = []
    contaminated_bags: list[dict] = []
    pasteurization_run_groups: dict[int, dict] = {}

    total_harvest_kg = 0.0
    total_dry_weight_kg = 0.0

    for bag in bags:
        contaminated = _is_contaminated(bag)
        bag_snapshot = _bag_history_snapshot(bag)
        lineage_metadata = _build_lineage_metadata(bag, bag_index, liquid_culture_memo, generation_memo)
        source_liquid_culture_id = lineage_metadata["source_liquid_culture_id"]
        source_liquid_culture_code = lineage_metadata["source_liquid_culture_code"]
        spawn_generation = lineage_metadata["spawn_generation"]
        contamination_by_bag_type_entries.append((bag.bag_type, bag.bag_type.title(), contaminated))

        if bag.species:
            contamination_by_species_entries.append(
                (bag.species.code, f"{bag.species.name} ({bag.species.code})", contaminated)
            )

        if source_liquid_culture_id is not None and source_liquid_culture_code is not None:
            contamination_by_liquid_culture_entries.append(
                (str(source_liquid_culture_id), source_liquid_culture_code, contaminated)
            )

        if bag.inoculation_source_type is not None:
            source_type_label = "Liquid Culture" if bag.inoculation_source_type == "LIQUID_CULTURE" else "Spawn Bag"
            contamination_by_inoculation_source_type_entries.append(
                (bag.inoculation_source_type, source_type_label, contaminated)
            )

        if spawn_generation is not None:
            contamination_by_spawn_generation_entries.append(
                (str(spawn_generation), f"Generation {spawn_generation}", contaminated)
            )

        source_sterilization_run = bag.sterilization_run
        if bag.bag_type == "SUBSTRATE" and bag.parent_spawn_bag is not None:
            source_sterilization_run = bag.parent_spawn_bag.sterilization_run
        if source_sterilization_run is not None:
            contamination_by_source_sterilization_entries.append(
                (str(source_sterilization_run.sterilization_run_id), source_sterilization_run.run_code, contaminated)
            )

        if contaminated:
            contaminated_bags.append(
                    {
                        "bag_id": bag.bag_id,
                        "bag_code": bag.bag_code,
                        "bag_ref": bag.bag_ref,
                        "bag_type": bag.bag_type,
                        "status": bag_snapshot["status"],
                        "disposal_reason": bag.disposal_reason,
                        "contaminated_at": bag_snapshot["disposed_at"],
                        "species_id": bag.species_id,
                        "species_code": bag.species.code if bag.species else None,
                        "species_name": bag.species.name if bag.species else None,
                    "sterilization_run_id": bag.sterilization_run_id,
                    "sterilization_run_code": bag.sterilization_run.run_code if bag.sterilization_run else None,
                    "pasteurization_run_id": bag.pasteurization_run_id,
                    "pasteurization_run_code": bag.pasteurization_run.run_code if bag.pasteurization_run else None,
                    "parent_spawn_bag_id": bag.parent_spawn_bag_id,
                    "parent_spawn_bag_ref": bag.parent_spawn_bag_ref,
                    "source_liquid_culture_id": source_liquid_culture_id,
                    "source_liquid_culture_code": source_liquid_culture_code,
                    "spawn_generation": spawn_generation,
                    "source_sterilization_run_id": (
                        source_sterilization_run.sterilization_run_id if source_sterilization_run is not None else None
                    ),
                    "source_sterilization_run_code": source_sterilization_run.run_code if source_sterilization_run else None,
                }
            )

        if bag.bag_type != "SUBSTRATE":
            continue

        pasteurization_run_code = bag.pasteurization_run.run_code if bag.pasteurization_run else None
        if bag.pasteurization_run_id is not None and pasteurization_run_code is not None:
            contamination_by_pasteurization_entries.append(
                (str(bag.pasteurization_run_id), pasteurization_run_code, contaminated)
            )

        if bag.parent_spawn_bag is not None:
            contamination_by_parent_spawn_entries.append(
                (bag.parent_spawn_bag.bag_id, bag.parent_spawn_bag.bag_ref, contaminated)
            )

        metrics_row = _build_substrate_metrics_row(bag, lineage_metadata)
        bag_total_harvest_kg = metrics_row["total_harvest_kg"]
        dry_weight_kg = metrics_row["dry_weight_kg"]
        if dry_weight_kg is not None:
            total_dry_weight_kg += dry_weight_kg
        total_harvest_kg += bag_total_harvest_kg
        substrate_rows.append(metrics_row)

        if bag.pasteurization_run_id is not None and pasteurization_run_code is not None:
            run_group = pasteurization_run_groups.setdefault(
                bag.pasteurization_run_id,
                {
                    "pasteurization_run_id": bag.pasteurization_run_id,
                    "run_code": pasteurization_run_code,
                    "total_bags": 0,
                    "contaminated_bags": 0,
                    "total_harvest_kg": 0.0,
                    "total_dry_weight_kg": 0.0,
                },
            )
            run_group["total_bags"] += 1
            if contaminated:
                run_group["contaminated_bags"] += 1
            run_group["total_harvest_kg"] += bag_total_harvest_kg
            if dry_weight_kg is not None:
                run_group["total_dry_weight_kg"] += dry_weight_kg

    total_bags = len(bags)
    total_contaminated_bags = sum(1 for bag in bags if _is_contaminated(bag))
    total_spawn_bags = sum(1 for bag in bags if bag.bag_type == "SPAWN")
    total_substrate_bags = len(substrate_rows)
    substrate_bags_with_harvest = sum(1 for row in substrate_rows if row["total_harvest_kg"] > 0)
    substrate_bags_with_dry_weight = sum(1 for row in substrate_rows if row["dry_weight_kg"] is not None)

    pasteurization_runs = []
    for row in pasteurization_run_groups.values():
        total_bags_in_group = row["total_bags"]
        contaminated_bag_count = row["contaminated_bags"]
        total_dry_weight_in_group = row["total_dry_weight_kg"]
        pasteurization_runs.append(
            {
                **row,
                "contamination_rate": contaminated_bag_count / total_bags_in_group if total_bags_in_group else 0.0,
                "bio_efficiency": (
                    row["total_harvest_kg"] / total_dry_weight_in_group
                    if total_dry_weight_in_group > 0
                    else None
                ),
            }
        )

    pasteurization_runs.sort(key=lambda row: row["run_code"])
    substrate_rows.sort(key=lambda row: row["bag_ref"])
    contaminated_bags.sort(
        key=lambda row: (
            row["contaminated_at"] is None,
            row["contaminated_at"] or datetime.min.replace(tzinfo=timezone.utc),
            row["bag_ref"],
        ),
        reverse=True,
    )

    return {
        "generated_at": _now(),
        "summary": {
            "total_spawn_bags": total_spawn_bags,
            "total_substrate_bags": total_substrate_bags,
            "total_contaminated_bags": total_contaminated_bags,
            "contamination_rate": total_contaminated_bags / total_bags if total_bags else 0.0,
            "substrate_bags_with_harvest": substrate_bags_with_harvest,
            "substrate_bags_with_dry_weight": substrate_bags_with_dry_weight,
            "total_harvest_kg": total_harvest_kg,
            "total_dry_weight_kg": total_dry_weight_kg,
            "overall_bio_efficiency": total_harvest_kg / total_dry_weight_kg if total_dry_weight_kg > 0 else None,
        },
        "contamination_by_bag_type": _build_group_summary(contamination_by_bag_type_entries),
        "contamination_by_species": _build_group_summary(contamination_by_species_entries),
        "contamination_by_liquid_culture": _build_group_summary(contamination_by_liquid_culture_entries),
        "contamination_by_inoculation_source_type": _build_group_summary(contamination_by_inoculation_source_type_entries),
        "contamination_by_spawn_generation": _build_group_summary(contamination_by_spawn_generation_entries),
        "contamination_by_source_sterilization_run": _build_group_summary(contamination_by_source_sterilization_entries),
        "contamination_by_pasteurization_run": _build_group_summary(contamination_by_pasteurization_entries),
        "contamination_by_parent_spawn_bag": _build_group_summary(contamination_by_parent_spawn_entries),
        "contaminated_bags": contaminated_bags,
        "data_quality_issues": _build_data_quality_issues(bags),
        "pasteurization_runs": pasteurization_runs,
        "substrate_bags": substrate_rows,
    }


_DASHBOARD_ACTIVITY_TITLES = {
    models.BagStatusEventType.CREATED.value: "Record created",
    models.BagStatusEventType.STERILIZED.value: "Sterilized",
    models.BagStatusEventType.PASTEURIZED.value: "Pasteurized",
    models.BagStatusEventType.BAG_CODE_ASSIGNED.value: "Bag code assigned",
    models.BagStatusEventType.INOCULATED.value: "Inoculated",
    models.BagStatusEventType.INCUBATION_STARTED.value: "Incubation started",
    models.BagStatusEventType.READY.value: "Ready",
    models.BagStatusEventType.FRUITING_STARTED.value: "Fruiting started",
    models.BagStatusEventType.HARVEST_RECORDED.value: "Harvest recorded",
    models.BagStatusEventType.CONSUMED.value: "Source consumed",
    models.BagStatusEventType.DISPOSED.value: "Disposed",
}


def _bag_matches_dashboard_queue(bag: models.Bag, snapshot: dict, *, bag_type: str, status: str) -> bool:
    return bag.bag_type == bag_type and snapshot["status"] == status


def _build_dashboard_queue_rows(bags: list[models.Bag], snapshots: dict[str, dict]) -> list[dict]:
    queue_specs = [
        {
            "key": "spawn_unlabeled",
            "label": "Spawn waiting for inoculation",
            "description": "Sterilized spawn records that still need species assignment and label printing.",
            "href": "/bags?bag_type=SPAWN&status=STERILIZED",
            "tone": "action",
            "predicate": lambda bag, snapshot: _bag_matches_dashboard_queue(
                bag,
                snapshot,
                bag_type="SPAWN",
                status="STERILIZED",
            ),
        },
        {
            "key": "spawn_ready",
            "label": "Ready spawn bags",
            "description": "Colonized spawn bags available to inoculate new spawn or substrate bags.",
            "href": "/bags?bag_type=SPAWN&status=READY",
            "tone": "action",
            "predicate": lambda bag, snapshot: _bag_matches_dashboard_queue(
                bag,
                snapshot,
                bag_type="SPAWN",
                status="READY",
            ),
        },
        {
            "key": "substrate_unlabeled",
            "label": "Substrate waiting for inoculation",
            "description": "Pasteurized substrate records that still need a ready spawn bag and printed code.",
            "href": "/bags?bag_type=SUBSTRATE&status=PASTEURIZED",
            "tone": "action",
            "predicate": lambda bag, snapshot: _bag_matches_dashboard_queue(
                bag,
                snapshot,
                bag_type="SUBSTRATE",
                status="PASTEURIZED",
            ),
        },
        {
            "key": "substrate_incubating",
            "label": "Substrate incubating",
            "description": "Substrate bags currently colonizing in the incubation tent.",
            "href": "/bags?bag_type=SUBSTRATE&status=INCUBATING",
            "tone": "default",
            "predicate": lambda bag, snapshot: _bag_matches_dashboard_queue(
                bag,
                snapshot,
                bag_type="SUBSTRATE",
                status="INCUBATING",
            ),
        },
        {
            "key": "substrate_ready",
            "label": "Ready for fruiting",
            "description": "Substrate bags ready to move from incubation into the grow tent.",
            "href": "/bags?bag_type=SUBSTRATE&status=READY",
            "tone": "action",
            "predicate": lambda bag, snapshot: _bag_matches_dashboard_queue(
                bag,
                snapshot,
                bag_type="SUBSTRATE",
                status="READY",
            ),
        },
        {
            "key": "substrate_fruiting",
            "label": "Fruiting now",
            "description": "Substrate bags currently in the grow tent and likely approaching harvest.",
            "href": "/bags?bag_type=SUBSTRATE&status=FRUITING",
            "tone": "default",
            "predicate": lambda bag, snapshot: _bag_matches_dashboard_queue(
                bag,
                snapshot,
                bag_type="SUBSTRATE",
                status="FRUITING",
            ),
        },
        {
            "key": "second_flush",
            "label": "Waiting for second flush",
            "description": "Substrate bags with a first flush recorded and a second harvest still pending.",
            "href": "/bags?bag_type=SUBSTRATE&status=FLUSH_1_COMPLETE",
            "tone": "default",
            "predicate": lambda bag, snapshot: _bag_matches_dashboard_queue(
                bag,
                snapshot,
                bag_type="SUBSTRATE",
                status="FLUSH_1_COMPLETE",
            ),
        },
        {
            "key": "contaminated",
            "label": "Contamination cases",
            "description": "Bags disposed for contamination that need review and traceability follow-up.",
            "href": "/bags?status=CONTAMINATED",
            "tone": "warning",
            "predicate": lambda bag, snapshot: snapshot["status"] == "CONTAMINATED",
        },
    ]

    rows = []
    for spec in queue_specs:
        count = sum(1 for bag in bags if spec["predicate"](bag, snapshots[bag.bag_id]))
        rows.append(
            {
                "key": spec["key"],
                "label": spec["label"],
                "count": count,
                "description": spec["description"],
                "href": spec["href"],
                "tone": spec["tone"],
            }
        )
    return rows


def _build_dashboard_run_summaries(db: Session) -> tuple[list[dict], list[dict]]:
    sterilization_runs = db.execute(
        select(models.SterilizationRun)
        .order_by(models.SterilizationRun.unloaded_at.desc(), models.SterilizationRun.sterilization_run_id.desc())
        .limit(6)
    ).scalars().all()
    pasteurization_runs = db.execute(
        select(models.PasteurizationRun)
        .order_by(models.PasteurizationRun.unloaded_at.desc(), models.PasteurizationRun.pasteurization_run_id.desc())
        .limit(6)
    ).scalars().all()

    sterilization_rows: list[dict] = []
    for run in sterilization_runs:
        detail = get_sterilization_run_detail(db, run.sterilization_run_id)
        if not detail:
            continue
        spawn_rows = detail["bags"]
        downstream_rows = detail["downstream_substrate_bags"]
        total_bags = len(spawn_rows)
        unlabeled_bags = sum(1 for row in spawn_rows if row["bag_code"] is None)
        ready_bags = sum(1 for row in spawn_rows if row["status"] == "READY")
        contaminated_bags = sum(1 for row in downstream_rows if row["contaminated"])
        harvested_bags = sum(1 for row in downstream_rows if row["total_harvest_kg"] > 0)
        downstream_bags = len(downstream_rows)

        if total_bags < run.bag_count:
            next_action = "Create bag records"
        elif unlabeled_bags > 0:
            next_action = "Inoculate unlabeled bags"
        elif ready_bags > 0:
            next_action = "Use ready spawn bags"
        elif downstream_bags > 0:
            next_action = "Review downstream outcomes"
        else:
            next_action = "Monitor run"

        sterilization_rows.append(
            {
                "run_type": "STERILIZATION",
                "run_id": run.sterilization_run_id,
                "run_code": run.run_code,
                "unloaded_at": _as_utc(run.unloaded_at),
                "planned_bag_count": run.bag_count,
                "total_bags": total_bags,
                "unlabeled_bags": unlabeled_bags,
                "ready_bags": ready_bags,
                "fruiting_bags": 0,
                "contaminated_bags": contaminated_bags,
                "harvested_bags": harvested_bags,
                "downstream_bags": downstream_bags,
                "next_action": next_action,
                "href": f"/sterilization-runs/{run.sterilization_run_id}",
            }
        )

    pasteurization_rows: list[dict] = []
    for run in pasteurization_runs:
        detail = get_pasteurization_run_detail(db, run.pasteurization_run_id)
        if not detail:
            continue
        bag_rows = detail["bags"]
        total_bags = len(bag_rows)
        unlabeled_bags = sum(1 for row in bag_rows if row["bag_code"] is None)
        ready_bags = sum(1 for row in bag_rows if row["status"] == "READY")
        fruiting_bags = sum(1 for row in bag_rows if row["status"] == "FRUITING")
        contaminated_bags = sum(1 for row in bag_rows if row["contaminated"])
        harvested_bags = sum(1 for row in bag_rows if row["total_harvest_kg"] > 0)

        if total_bags < run.bag_count:
            next_action = "Create bag records"
        elif unlabeled_bags > 0:
            next_action = "Inoculate unlabeled bags"
        elif ready_bags > 0:
            next_action = "Move ready bags to fruiting"
        elif fruiting_bags > 0:
            next_action = "Record harvests"
        elif contaminated_bags > 0:
            next_action = "Review contamination"
        else:
            next_action = "Monitor run"

        pasteurization_rows.append(
            {
                "run_type": "PASTEURIZATION",
                "run_id": run.pasteurization_run_id,
                "run_code": run.run_code,
                "unloaded_at": _as_utc(run.unloaded_at),
                "planned_bag_count": run.bag_count,
                "total_bags": total_bags,
                "unlabeled_bags": unlabeled_bags,
                "ready_bags": ready_bags,
                "fruiting_bags": fruiting_bags,
                "contaminated_bags": contaminated_bags,
                "harvested_bags": harvested_bags,
                "downstream_bags": total_bags,
                "next_action": next_action,
                "href": f"/pasteurization-runs/{run.pasteurization_run_id}",
            }
        )

    return sterilization_rows, pasteurization_rows


def _build_dashboard_recent_activity(bags: list[models.Bag], *, limit: int = 12) -> list[dict]:
    rows: list[dict] = []
    for bag in bags:
        for event in bag.status_events:
            rows.append(
                {
                    "occurred_at": _as_utc(event.occurred_at) or _now(),
                    "bag_id": bag.bag_id,
                    "bag_ref": bag.bag_ref,
                    "bag_type": bag.bag_type,
                    "event_type": event.event_type,
                    "title": _DASHBOARD_ACTIVITY_TITLES.get(event.event_type, event.event_type.replace("_", " ").title()),
                    "detail": event.detail,
                    "href": f"/bags/{bag.bag_ref}",
                    "_sort_id": event.bag_status_event_id or 0,
                }
            )

    rows.sort(
        key=lambda row: (
            row["occurred_at"],
            row["_sort_id"],
        ),
        reverse=True,
    )
    return [{key: value for key, value in row.items() if not key.startswith("_")} for row in rows[:limit]]


def _build_dashboard_alerts(report: dict) -> list[dict]:
    alerts: list[dict] = []
    contaminated_bags = report["contaminated_bags"]
    if contaminated_bags:
        recent_refs = ", ".join(row["bag_ref"] for row in contaminated_bags[:3])
        alerts.append(
            {
                "severity": "warning",
                "title": f"{len(contaminated_bags)} contamination case(s) require review",
                "detail": f"Most recent affected bags: {recent_refs}.",
                "href": "/reports",
            }
        )

    for issue in report["data_quality_issues"][:4]:
        sample_refs = ", ".join(issue["bag_refs"]) if issue["bag_refs"] else "No examples captured"
        alerts.append(
            {
                "severity": "warning",
                "title": issue["label"],
                "detail": f"{issue['count']} bag(s) affected. Examples: {sample_refs}.",
                "href": "/reports",
            }
        )

    if not alerts:
        alerts.append(
            {
                "severity": "info",
                "title": "No active alerts",
                "detail": "No contamination or data-quality issues are flagged right now.",
                "href": "/reports",
            }
        )

    return alerts


def get_dashboard_overview(db: Session) -> dict:
    bags = db.execute(
        select(models.Bag)
        .options(*_bag_lineage_options())
        .order_by(models.Bag.created_at.desc(), models.Bag.bag_id.desc())
    ).unique().scalars().all()
    snapshots = {bag.bag_id: _bag_history_snapshot(bag) for bag in bags}
    report = get_production_report(db)
    sterilization_rows, pasteurization_rows = _build_dashboard_run_summaries(db)

    return {
        "generated_at": _now(),
        "summary": report["summary"],
        "queues": _build_dashboard_queue_rows(bags, snapshots),
        "sterilization_runs": sterilization_rows,
        "pasteurization_runs": pasteurization_rows,
        "recent_activity": _build_dashboard_recent_activity(bags),
        "alerts": _build_dashboard_alerts(report),
    }
