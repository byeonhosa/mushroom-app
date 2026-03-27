"""
Dashboard overview: queue cards, run summaries, recent activity, and alerts.
"""
from sqlalchemy.orm import Session
from sqlalchemy import select

from . import models
from .crud_status import (
    _now,
    _as_utc,
    _bag_history_snapshot,
    _bag_lineage_options,
)
from .crud_reporting import (
    get_production_report,
    get_sterilization_run_detail,
    get_pasteurization_run_detail,
)


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
