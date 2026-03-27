"""
Reporting, metrics, and run-detail views.

Imports from crud_status for shared helpers; no imports from crud_bags or crud_dashboard.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import select

from . import models
from .crud_status import (
    _now,
    _as_utc,
    _bag_history_snapshot,
    _bag_lineage_options,
    _build_descendant_bags,
)


def _is_contaminated(bag: models.Bag) -> bool:
    return bag.disposal_reason == "CONTAMINATION"


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
