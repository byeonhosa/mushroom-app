"""
Status derivation, event recording, and shared bag-query helpers.

This is the base layer — no imports from other crud_* modules.
All other crud modules import from here.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from . import models


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
