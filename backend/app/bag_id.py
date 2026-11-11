"""Bag identity: internal record IDs, printable bag codes, and run codes.

Three identifiers are issued here.

Internal ID (`SPNREC-0001`, `SUBREC-0001`): given when a bag record is created,
never changes. Numbers come from a counter row that is updated in the caller's
transaction, so two people creating bags at the same moment cannot be handed
the same number (SRS BAG-11).

Bag code (`SB-LM-261109A-07`): printed on the label, given at inoculation.
Type, species code, run code, and the bag's number within its run (BAG-5).
With a species code of two or three characters, a standard run code and at
most 999 bags in a run, it is never longer than 18 characters.

Run code (`261109A`): the run's date as YYMMDD and a letter for the run's
place in that day (RUN-6). Sterilization and pasteurization runs are numbered
separately; the bag code's SP or SB prefix tells them apart.
"""

import re
import string
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .errors import ConflictError

STANDARD_RUN_CODE = re.compile(r"^\d{6}[A-Z]$")
SPECIES_CODE = re.compile(r"^[A-Z0-9]{2,3}$")
BAG_CODE_MAX_LENGTH = 18

_BAG_TYPE_PREFIX = {"SPAWN": "SP", "SUBSTRATE": "SB"}
_INTERNAL_PREFIX = {"SPAWN": "SPNREC", "SUBSTRATE": "SUBREC"}
_TRAILING_NUMBER = re.compile(r"-(\d+)$")


# --------------------------------------------------------------- internal IDs

def _highest_existing_seq(db: Session, prefix: str) -> int:
    """Highest number already used for `prefix-NNNN` internal IDs."""
    rows = db.execute(
        select(models.Bag.bag_id).where(models.Bag.bag_id.like(f"{prefix}-%"))
    ).scalars().all()
    highest = 0
    for value in rows:
        match = re.fullmatch(rf"{re.escape(prefix)}-(\d+)", value or "")
        if match:
            highest = max(highest, int(match.group(1)))
    return highest


def _reserve(db: Session, counter_name: str, count: int) -> int:
    """Reserve `count` consecutive numbers and return the first.

    The UPDATE takes a row lock on PostgreSQL that is held until the caller
    commits, so concurrent callers queue up behind one another. If the counter
    row does not exist yet (a database built without migration 024's seed) it
    is created from the highest number in use.
    """
    for _ in range(3):
        reserved_up_to = db.execute(
            update(models.IdCounter)
            .where(models.IdCounter.name == counter_name)
            .values(next_value=models.IdCounter.next_value + count)
            .returning(models.IdCounter.next_value)
        ).scalar_one_or_none()
        if reserved_up_to is not None:
            return reserved_up_to - count
        try:
            with db.begin_nested():
                db.add(
                    models.IdCounter(
                        name=counter_name,
                        next_value=_highest_existing_seq(db, counter_name) + 1,
                    )
                )
        except IntegrityError:
            # Another request created the row between our UPDATE and INSERT.
            continue
    raise RuntimeError(f"Could not reserve bag numbers from counter {counter_name}")


def generate_internal_bag_ids(db: Session, bag_type: str, count: int) -> list[str]:
    prefix = _INTERNAL_PREFIX[bag_type]
    first = _reserve(db, prefix, count)
    return [f"{prefix}-{first + offset:04d}" for offset in range(count)]


# ------------------------------------------------------------------ run codes

def farm_today() -> date:
    return datetime.now(ZoneInfo(settings.farm_timezone)).date()


def farm_date(moment: datetime) -> date:
    """The calendar day at the farm on which `moment` fell."""
    return moment.astimezone(ZoneInfo(settings.farm_timezone)).date()


def next_run_code(db: Session, run_model, on: date | None = None) -> str:
    """The first unused code for a day: 261109A, then 261109B, and so on."""
    day = on or farm_today()
    stem = day.strftime("%y%m%d")
    used = set(
        db.execute(select(run_model.run_code).where(run_model.run_code.like(f"{stem}_"))).scalars().all()
    )
    for letter in string.ascii_uppercase:
        if f"{stem}{letter}" not in used:
            return f"{stem}{letter}"
    raise ConflictError(f"All 26 run codes for {day.isoformat()} are in use.")


# ------------------------------------------------------------------ bag codes

def _run_key(run_code: str) -> str:
    """The run's part of a bag code.

    A standard run code is used as it is. A run created before the standard
    (or by a test) keeps its own code, cleaned of anything a scanner or a
    label could trip on; its bag codes are longer than 18 characters but
    still unique and still free of the repeated prefix.
    """
    code = run_code.strip().upper()
    if STANDARD_RUN_CODE.fullmatch(code):
        return code
    return re.sub(r"[^A-Z0-9]+", "-", code).strip("-")[:40]


def _highest_bag_number_in_run(db: Session, run_column, run_id: int) -> int:
    codes = db.execute(
        select(models.Bag.bag_code).where(run_column == run_id, models.Bag.bag_code.is_not(None))
    ).scalars().all()
    highest = 0
    for code in codes:
        match = _TRAILING_NUMBER.search(code)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest


def _generate_bag_codes(
    db: Session,
    *,
    bag_type: str,
    run_model,
    run_id_column,
    bag_run_column,
    run_id: int,
    species_id: int,
    count: int,
) -> list[str]:
    # Lock the run row so that two inoculation sessions on the same run take
    # their bag numbers one after the other. SQLite has a single writer and
    # ignores the lock clause.
    run = db.execute(
        select(run_model).where(run_id_column == run_id).with_for_update()
    ).scalar_one_or_none()
    if not run:
        raise ValueError(f"Run {run_id} not found")
    species = db.get(models.MushroomSpecies, species_id)
    if not species:
        raise ValueError(f"Species {species_id} not found")

    stem = f"{_BAG_TYPE_PREFIX[bag_type]}-{species.code.strip().upper()}-{_run_key(run.run_code)}"
    width = 2 if (run.bag_count or 0) <= 99 else 3
    first = _highest_bag_number_in_run(db, bag_run_column, run_id) + 1
    return [f"{stem}-{first + offset:0{width}d}" for offset in range(count)]


def generate_spawn_bag_ids(db: Session, sterilization_run_id: int, species_id: int, count: int) -> list[str]:
    """`count` printable codes for spawn bags of one run and species."""
    return _generate_bag_codes(
        db,
        bag_type="SPAWN",
        run_model=models.SterilizationRun,
        run_id_column=models.SterilizationRun.sterilization_run_id,
        bag_run_column=models.Bag.sterilization_run_id,
        run_id=sterilization_run_id,
        species_id=species_id,
        count=count,
    )


def generate_substrate_bag_ids(db: Session, pasteurization_run_id: int, species_id: int, count: int) -> list[str]:
    """`count` printable codes for substrate bags of one run and species."""
    return _generate_bag_codes(
        db,
        bag_type="SUBSTRATE",
        run_model=models.PasteurizationRun,
        run_id_column=models.PasteurizationRun.pasteurization_run_id,
        bag_run_column=models.Bag.pasteurization_run_id,
        run_id=pasteurization_run_id,
        species_id=species_id,
        count=count,
    )
