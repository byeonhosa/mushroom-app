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


def _event_time_by_type(bag: models.Bag) -> dict[str, datetime]:
    event_times: dict[str, datetime] = {}
    for event in sorted(
        bag.status_events,
        key=lambda row: (_as_utc(row.occurred_at) or _now(), row.bag_status_event_id or 0),
    ):
        event_times[event.event_type] = _as_utc(event.occurred_at) or _now()
    return event_times


def _derive_bag_status(bag: models.Bag, times: dict) -> str:
    """The one place a bag's status is worked out (SRS MNT-3).

    `times` is the stage timeline from `_bag_history_snapshot`: the event
    history first, with the cached column as the fallback for a bag that has
    no event of that type. A bag record is created from a run that has already
    been heat-treated, so the starting status is STERILIZED or PASTEURIZED.
    """
    if times["disposed_at"]:
        return "CONTAMINATED" if bag.disposal_reason == "CONTAMINATION" else "DISPOSED"

    if bag.bag_type == "SPAWN":
        if times["consumed_at"]:
            return "CONSUMED"
    else:
        harvest_count = len(bag.harvest_events)
        if harvest_count >= 2:
            return "FLUSH_2_COMPLETE"
        if harvest_count >= 1:
            return "FLUSH_1_COMPLETE"
        if times["fruiting_start_at"]:
            return "FRUITING"

    if times["ready_at"]:
        return "READY"
    if times["incubation_start_at"]:
        return "INCUBATING"
    if times["inoculated_at"]:
        return "INOCULATED"
    return "STERILIZED" if bag.bag_type == "SPAWN" else "PASTEURIZED"


def _bag_history_snapshot(bag: models.Bag) -> dict:
    event_times = _event_time_by_type(bag)
    event_type = models.BagStatusEventType

    def stage_time(kind: models.BagStatusEventType, cached: datetime | None) -> datetime | None:
        return event_times.get(kind.value) or _as_utc(cached)

    snapshot = {
        "created_at": stage_time(event_type.CREATED, bag.created_at),
        "labeled_at": stage_time(event_type.BAG_CODE_ASSIGNED, bag.labeled_at),
        "inoculated_at": stage_time(event_type.INOCULATED, bag.inoculated_at),
        "incubation_start_at": stage_time(event_type.INCUBATION_STARTED, bag.incubation_start_at),
        "ready_at": stage_time(event_type.READY, bag.ready_at),
        "fruiting_start_at": stage_time(event_type.FRUITING_STARTED, bag.fruiting_start_at),
        "disposed_at": stage_time(event_type.DISPOSED, bag.disposed_at),
        "consumed_at": stage_time(event_type.CONSUMED, bag.consumed_at),
    }
    snapshot["status"] = _derive_bag_status(bag, snapshot)
    return snapshot


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
        # Set on the session by app.auth.get_principal (USR-4).
        recorded_by_user_id=db.info.get("user_id"),
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
        joinedload(models.Bag.source_purchased_spawn_lot),
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
