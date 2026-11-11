"""A realistic farm, generated (lead developer brief, section 7).

    python -m app.seed_demo                  # twelve weeks at the farm's own volume: about 1,000 bags
    python -m app.seed_demo --scale 10       # about 10,000 bags, for performance work
    python -m app.seed_demo --seed 7 --weeks 4 --end-date 2026-11-10

What it makes: purchased spawn lots arriving every other week, liquid cultures,
sterilization runs of spawn bags, pasteurization runs of substrate bags,
inoculation from bought spawn and from the farm's own spawn, incubation, ready,
fruiting, two flushes of harvest, disposal, a contamination rate of a few
percent, and one pasteurization run that went badly wrong.

How it works: it is a simulation, not a table loader. Every step is recorded
through the same functions the screens call, with the app's clock
(`app.clock`) set to the moment the step would have happened. So bag codes,
statuses, event histories and lineage are exactly what the app would hold had
operators done this work, and a fault in those functions shows up here too.

Deterministic: the same seed, scale, weeks and end date give the same farm,
bag for bag and gram for gram. The story ends at 6 pm on the end date, which
is yesterday unless given, so nothing is stamped in the future.

Safe by default: it refuses to run when the database already holds runs, bags,
purchased lots, cultures or harvests, and refuses in production, unless told
otherwise with a flag for each. It is never run by the deploy workflow.
"""

from __future__ import annotations

import argparse
import heapq
import itertools
import random
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import bag_id, clock, crud, models, seed_species
from .config import settings
from .db import SessionLocal

DEMO_NOTE = "Demo data"

# The app accepts flush 1 and flush 2 today. HAR-3 (WP-4) makes the limit a
# setting; raise this with it.
FLUSH_LIMIT = 2

# Runs a week at scale 1. The farm starts fewer than 100 substrate bags a week
# and buys most of its spawn.
PASTEURIZATION_RUNS_PER_WEEK = 2.0
STERILIZATION_RUNS_PER_WEEK = 0.5
PASTEURIZATION_DAYS = (1, 3, 0, 2, 4)  # Tuesday and Thursday first, then the rest of the week
STERILIZATION_DAYS = (0, 2, 4, 1, 3)
MAX_SCALE = 50  # 26 run codes a day is the limit

BASE_CONTAMINATION = 0.03
BAD_RUN_CONTAMINATION = 0.45
LATE_CONTAMINATION = 0.02  # after the first flush
SPAWN_CONTAMINATION = 0.04
OWN_SPAWN_SHARE = 0.4  # of substrate sessions, when the farm has ready spawn of that species
SECOND_FLUSH_SHARE = 0.75

# How often each variety is grown, relative to the others. A variety not
# listed here counts as 1.
SPECIES_WEIGHT = {"BO": 5, "LM": 4, "KT": 2, "STK": 2, "CNT": 2, "WO": 2}

VENDORS = ("Blue Ridge Spawn Co.", "Valley Mycology Supply")


class DemoDataRefused(RuntimeError):
    """The generator will not run here without an explicit override."""


@dataclass(frozen=True)
class DemoConfig:
    seed: int = 1
    scale: float = 1.0
    weeks: int = 12
    end_date: date | None = None

    def validate(self) -> None:
        if not 0 < self.scale <= MAX_SCALE:
            raise ValueError(f"--scale must be more than 0 and at most {MAX_SCALE}.")
        if not 1 <= self.weeks <= 104:
            raise ValueError("--weeks must be between 1 and 104.")


@dataclass
class LedgerEntry:
    """What the generator itself decided about one bag.

    Kept apart from the database on purpose: a test adds these up on its own
    and compares the totals with what the reports say.
    """

    bag_type: str
    bag_code: str
    species_code: str
    run_code: str
    source_type: str
    source_code: str
    dry_kg: float | None = None
    contaminated: bool = False
    harvests_kg: list[float] = field(default_factory=list)


@dataclass
class DemoResult:
    config: DemoConfig
    first_day: date
    last_day: date
    ledger: dict[str, LedgerEntry]
    bad_run_code: str | None
    counts: dict[str, int]
    fill_dry_kg: float

    def lines(self) -> list[str]:
        spawn = [e for e in self.ledger.values() if e.bag_type == "SPAWN"]
        substrate = [e for e in self.ledger.values() if e.bag_type == "SUBSTRATE"]
        contaminated = sum(1 for e in self.ledger.values() if e.contaminated)
        harvest = sum(sum(e.harvests_kg) for e in substrate)
        total = len(self.ledger)
        return [
            f"Demo farm from {self.first_day} to {self.last_day} "
            f"(seed {self.config.seed}, scale {self.config.scale:g}, {self.config.weeks} weeks)",
            f"  sterilization runs:    {self.counts['sterilization_runs']}",
            f"  pasteurization runs:   {self.counts['pasteurization_runs']}"
            + (f" (the bad one: {self.bad_run_code})" if self.bad_run_code else ""),
            f"  purchased spawn lots:  {self.counts['purchased_spawn_lots']}",
            f"  liquid cultures:       {self.counts['liquid_cultures']}",
            f"  bag records:           {self.counts['bag_records']}",
            f"  inoculated spawn bags: {len(spawn)}",
            f"  inoculated substrate:  {len(substrate)}",
            f"  harvests:              {self.counts['harvest_events']} ({harvest:.1f} kg)",
            f"  contaminated:          {contaminated}"
            + (f" ({contaminated / total:.1%} of inoculated bags)" if total else ""),
        ]


# --------------------------------------------------------------- safety checks

# Records of work. Reference rows (species, recipes, fill profiles, grain types)
# do not count, and nor do mix lots: migration 015 seeds one, and a real
# one is always followed by a pasteurization run, which does count.
_FARM_TABLES = (
    ("sterilization runs", models.SterilizationRun),
    ("pasteurization runs", models.PasteurizationRun),
    ("bags", models.Bag),
    ("purchased spawn lots", models.PurchasedSpawnLot),
    ("liquid cultures", models.LiquidCulture),
    ("harvests", models.HarvestEvent),
)


def existing_farm_data(db: Session) -> dict[str, int]:
    """Tables that already hold farm records, with their row counts."""
    found = {}
    for label, model in _FARM_TABLES:
        count = db.execute(select(func.count()).select_from(model)).scalar_one()
        if count:
            found[label] = count
    return found


def _check_allowed(db: Session, *, allow_existing_data: bool, allow_production: bool) -> None:
    if settings.is_production and not allow_production:
        raise DemoDataRefused(
            "This is the production environment. Demo data is not written here "
            "unless --allow-production is given."
        )
    found = existing_farm_data(db)
    if found and not allow_existing_data:
        held = ", ".join(f"{count} {label}" for label, count in found.items())
        raise DemoDataRefused(
            f"The database already holds {held}. Demo data is not added to existing "
            "records unless --allow-existing-data is given."
        )


# ------------------------------------------------------------------ simulation

@dataclass(frozen=True)
class _Species:
    species_id: int
    code: str
    name: str
    colonization_days: tuple[int, int]
    pin_to_harvest_days: tuple[int, int]
    efficiency_pct: tuple[int, int]


def _range(low, high, fallback: tuple[int, int], floor: int, ceiling: int) -> tuple[int, int]:
    """A profile range, with the fallback for a value no source gave."""
    low = fallback[0] if low is None else int(low)
    high = fallback[1] if high is None else int(high)
    low = max(floor, min(ceiling, low))
    high = max(low, min(ceiling, high))
    return low, high


class _Simulation:
    def __init__(self, db: Session, config: DemoConfig):
        self.db = db
        self.config = config
        self.rng = random.Random(config.seed)
        self.zone = ZoneInfo(settings.farm_timezone)

        last_day = config.end_date or (bag_id.farm_today() - timedelta(days=1))
        self.last_day = last_day
        self.first_day = last_day - timedelta(days=config.weeks * 7 - 1)
        self.end = self.local(last_day, 18, 0)

        self.now = self.local(self.first_day, 8, 0)
        self._queue: list[tuple[datetime, int, Callable[[], None]]] = []
        self._order = itertools.count()
        self._handled = 0

        self.ledger: dict[str, LedgerEntry] = {}
        self.counts: dict[str, int] = defaultdict(int)
        self.bad_run_code: str | None = None

        self.species: list[_Species] = []
        self.cultures: dict[str, tuple[int, str]] = {}  # species code -> (id, culture code)
        self.open_lots: dict[str, tuple[int, str]] = {}  # species code -> (id, lot code)
        self.ready_spawn: dict[str, deque[str]] = defaultdict(deque)
        self.reference: dict[str, int | list[int]] = {}

    # ------------------------------------------------------------ time

    def local(self, day: date, hour: int, minute: int = 0) -> datetime:
        return datetime(day.year, day.month, day.day, hour, minute, tzinfo=self.zone).astimezone(timezone.utc)

    def day_of(self, moment: datetime) -> date:
        return moment.astimezone(self.zone).date()

    def tick(self, seconds: int = 20) -> None:
        """Time passes while the operator works through a batch."""
        self.now += timedelta(seconds=seconds)

    def at(self, when: datetime, action: Callable[[], None]) -> None:
        """Do `action` at `when`. Anything after the end of the story never happens."""
        if when <= self.end:
            heapq.heappush(self._queue, (when, next(self._order), action))

    def work_moment(self) -> tuple[int, int]:
        """A time of day when someone is at the farm, to five minutes."""
        return self.rng.randint(8, 16), self.rng.randrange(0, 60, 5)

    def run(self) -> None:
        with clock.simulated(lambda: self.now):
            while self._queue:
                when, _, action = heapq.heappop(self._queue)
                self.now = when
                action()
                self._handled += 1
                if self._handled % 200 == 0:
                    # Nothing here keeps a loaded row between steps, only ids and codes.
                    self.db.expunge_all()

    # ------------------------------------------------------- reference data

    def _first_or_create(self, model, where, create: Callable[[], object]):
        found = self.db.execute(select(model).where(where)).scalars().first()
        return found if found is not None else create()

    def set_up(self) -> None:
        db = self.db
        if db.execute(select(func.count()).select_from(models.MushroomSpecies)).scalar_one() == 0:
            seed_species.seed(db)

        grown = db.execute(
            select(models.MushroomSpecies)
            .where(models.MushroomSpecies.is_active.is_(True), models.MushroomSpecies.in_rotation_now.is_(True))
            .order_by(models.MushroomSpecies.code)
        ).scalars().all()
        if not grown:
            grown = db.execute(
                select(models.MushroomSpecies)
                .where(models.MushroomSpecies.is_active.is_(True))
                .order_by(models.MushroomSpecies.code)
            ).scalars().all()[:6]
        if not grown:
            raise DemoDataRefused("There is no active species to grow.")
        for row in grown:
            profile = row.profile
            self.species.append(
                _Species(
                    species_id=row.species_id,
                    code=row.code,
                    name=row.name,
                    colonization_days=_range(
                        getattr(profile, "colonization_days_low", None),
                        getattr(profile, "colonization_days_high", None),
                        (14, 21), 7, 60,
                    ),
                    pin_to_harvest_days=_range(
                        getattr(profile, "pin_to_harvest_days_low", None),
                        getattr(profile, "pin_to_harvest_days_high", None),
                        (5, 8), 2, 21,
                    ),
                    efficiency_pct=_range(
                        getattr(profile, "biological_efficiency_pct_low", None),
                        getattr(profile, "biological_efficiency_pct_high", None),
                        (60, 90), 30, 150,
                    ),
                )
            )

        grains = [
            self._first_or_create(
                models.GrainType,
                models.GrainType.name == name,
                lambda name=name: crud.create_grain_type(db, {"name": name, "notes": DEMO_NOTE}),
            ).grain_type_id
            for name in ("Rye berries", "Millet")
        ]
        spawn_recipe = self._first_or_create(
            models.SpawnRecipe,
            models.SpawnRecipe.recipe_code == "GRAIN-1",
            lambda: crud.create_spawn_recipe(db, {"recipe_code": "GRAIN-1", "notes": DEMO_NOTE}),
        )
        fill_profile = self._first_or_create(
            models.FillProfile,
            models.FillProfile.name == "5 lb block",
            lambda: crud.create_fill_profile(db, "5 lb block", 0.95, 1.32, DEMO_NOTE),
        )
        recipes = [
            self._first_or_create(
                models.SubstrateRecipeVersion,
                models.SubstrateRecipeVersion.recipe_code == code,
                lambda name=name, code=code: crud.create_substrate_recipe_version(
                    db, {"name": name, "recipe_code": code, "notes": DEMO_NOTE}
                ),
            ).substrate_recipe_version_id
            for name, code in (("Masters Mix", "MM"), ("Hardwood and bran", "HB"))
        ]
        self.reference = {
            "grain_type_ids": grains,
            "spawn_recipe_id": spawn_recipe.spawn_recipe_id,
            "fill_profile_id": fill_profile.fill_profile_id,
            "fill_dry_kg": float(fill_profile.target_dry_kg_per_bag),
            "substrate_recipe_ids": recipes,
        }

        stamp = self.first_day.strftime("%y%m%d")
        for species in self.species:
            code = f"LC-{species.code}-{stamp}"
            culture = self._first_or_create(
                models.LiquidCulture,
                models.LiquidCulture.culture_code == code,
                lambda species=species, code=code: crud.create_liquid_culture(
                    db,
                    {
                        "culture_code": code,
                        "species_id": species.species_id,
                        "source": "Culture bank",
                        "prepared_at": self.now,
                        "notes": DEMO_NOTE,
                    },
                ),
            )
            self.cultures[species.code] = (culture.liquid_culture_id, culture.culture_code)
            self.counts["liquid_cultures"] += 1

    # ------------------------------------------------------------- planning

    def _runs_in_week(self, rate: float, carry: list[float]) -> int:
        carry[0] += rate
        count = int(carry[0])
        carry[0] -= count
        return count

    def plan(self) -> None:
        scale = self.config.scale
        # The first week always has a run of each kind, whatever the scale.
        past_carry = [max(0.0, 1 - PASTEURIZATION_RUNS_PER_WEEK * scale)]
        ster_carry = [max(0.0, 1 - STERILIZATION_RUNS_PER_WEEK * scale)]
        pasteurizations: list[tuple[date, int]] = []
        sterilizations: list[tuple[date, int]] = []

        week_start = self.first_day - timedelta(days=self.first_day.weekday())
        while week_start <= self.last_day:
            for count, days, plan in (
                (self._runs_in_week(PASTEURIZATION_RUNS_PER_WEEK * scale, past_carry), PASTEURIZATION_DAYS, pasteurizations),
                (self._runs_in_week(STERILIZATION_RUNS_PER_WEEK * scale, ster_carry), STERILIZATION_DAYS, sterilizations),
            ):
                on_day: dict[date, int] = defaultdict(int)
                for index in range(count):
                    day = week_start + timedelta(days=days[index % len(days)])
                    if self.first_day <= day <= self.last_day:
                        plan.append((day, on_day[day]))
                        on_day[day] += 1
            week_start += timedelta(days=7)

        # One run in the middle third goes badly, early enough for it to show.
        bad_index = None
        if len(pasteurizations) >= 3:
            third = len(pasteurizations) // 3
            bad_index = self.rng.randrange(third, max(third + 1, 2 * third))

        delivery = self.first_day
        while delivery <= self.last_day:
            self.at(self.local(delivery, 11, 0), self.receive_deliveries)
            delivery += timedelta(days=14)

        for day, nth in sterilizations:
            self.at(self.local(day, 14, 0) + timedelta(minutes=10 * nth), self.sterilization_run)
        for index, (day, nth) in enumerate(pasteurizations):
            self.at(
                self.local(day, 15, 0) + timedelta(minutes=10 * nth),
                lambda bad=(index == bad_index): self.pasteurization_run(bad),
            )

    # ------------------------------------------------------- purchased spawn

    def receive_lot(self, species: _Species) -> tuple[int, str]:
        previous = self.open_lots.get(species.code)
        if previous is not None:
            crud.update_purchased_spawn_lot(self.db, previous[0], {"used_up": True})
        lot = crud.create_purchased_spawn_lot(
            self.db,
            {
                "vendor": self.rng.choice(VENDORS),
                "vendor_lot_number": str(self.rng.randint(10000, 99999)),
                "species_id": species.species_id,
                "grain_type_id": self.rng.choice(self.reference["grain_type_ids"]),
                "received_at": self.now,
                "quantity": self.rng.randint(2, 6),
                "quantity_unit": "bags",
                "notes": DEMO_NOTE,
            },
        )
        self.counts["purchased_spawn_lots"] += 1
        self.open_lots[species.code] = (lot.purchased_spawn_lot_id, lot.lot_code)
        return self.open_lots[species.code]

    def receive_deliveries(self) -> None:
        for species in self.species:
            self.receive_lot(species)
            self.tick(60)

    def lot_for(self, species: _Species) -> tuple[int, str]:
        return self.open_lots.get(species.code) or self.receive_lot(species)

    # ----------------------------------------------------------------- spawn

    def pick_species(self, most: int) -> list[_Species]:
        """One to `most` different varieties, the popular ones more often."""
        pool = list(self.species)
        wanted = min(most, len(pool))
        chosen = []
        for _ in range(wanted):
            weights = [SPECIES_WEIGHT.get(s.code, 1) for s in pool]
            pick = self.rng.choices(pool, weights=weights)[0]
            pool.remove(pick)
            chosen.append(pick)
        return chosen

    def split(self, total: int, parts: int, smallest: int) -> list[int]:
        """`total` bags over `parts` sessions, none smaller than `smallest`."""
        parts = max(1, min(parts, total // smallest))
        sizes = [smallest] * parts
        for _ in range(total - smallest * parts):
            sizes[self.rng.randrange(parts)] += 1
        return sizes

    def sterilization_run(self) -> None:
        db = self.db
        day = self.day_of(self.now)
        bag_count = self.rng.randint(6, 10)
        run = crud.create_sterilization_run(
            db,
            {
                "run_code": bag_id.next_run_code(db, models.SterilizationRun, day),
                "spawn_recipe_id": self.reference["spawn_recipe_id"],
                "grain_type_id": self.rng.choice(self.reference["grain_type_ids"]),
                "cycle_start_at": self.local(day, 9, 0),
                "cycle_end_at": self.local(day, 12, 0),
                "unloaded_at": self.now,
                "bag_count": bag_count,
                "temp_c": 121,
                "psi": 15,
                "hold_minutes": 150,
                "notes": DEMO_NOTE,
            },
        )
        self.counts["sterilization_runs"] += 1
        self.tick(300)
        crud.create_spawn_bags(db, run.sterilization_run_id, bag_count)
        self.counts["bag_records"] += bag_count
        self.counts["spawn_bag_records"] += bag_count
        run_id, run_code = run.sterilization_run_id, run.run_code
        self.at(
            self.local(day + timedelta(days=1), 9, 30) + timedelta(minutes=self.rng.randrange(0, 30, 5)),
            lambda: self.inoculate_spawn(run_id, run_code, bag_count),
        )

    def inoculate_spawn(self, run_id: int, run_code: str, bag_count: int) -> None:
        varieties = self.pick_species(1 if self.rng.random() < 0.6 else 2)
        for species, size in zip(varieties, self.split(bag_count, len(varieties), 3)):
            if self.rng.random() < 0.8:
                culture_id, source_code = self.cultures[species.code]
                bags = crud.inoculate_spawn_bags(
                    self.db, run_id, size, "LIQUID_CULTURE", liquid_culture_id=culture_id
                )
                source_type = "LIQUID_CULTURE"
            else:
                lot_id, source_code = self.lot_for(species)
                bags = crud.inoculate_spawn_bags(
                    self.db, run_id, size, "PURCHASED_SPAWN", purchased_spawn_lot_id=lot_id
                )
                source_type = "PURCHASED_SPAWN"
            codes = [bag.bag_code for bag in bags]
            for code in codes:
                self.ledger[code] = LedgerEntry("SPAWN", code, species.code, run_code, source_type, source_code)
            self.start_incubation(codes)
            self.plan_spawn_bags(codes, species)
            self.tick(600)

    def start_incubation(self, codes: list[str]) -> None:
        self.tick(120)
        for code in codes:
            crud.update_bag_incubation_start(self.db, code)
            self.tick()

    def plan_spawn_bags(self, codes: list[str], species: _Species) -> None:
        inoculated = self.day_of(self.now)
        ready_day = inoculated + timedelta(days=self.rng.randint(12, 18))
        hour, minute = self.work_moment()
        for index, code in enumerate(codes):
            offset = timedelta(seconds=20 * index)
            if self.rng.random() < SPAWN_CONTAMINATION:
                found = inoculated + timedelta(days=self.rng.randint(4, 10))
                self.at(self.local(found, hour, minute) + offset, lambda code=code: self.dispose(code, "CONTAMINATION"))
                continue
            self.at(
                self.local(ready_day, hour, minute) + offset,
                lambda code=code: self.spawn_ready(code, species.code),
            )

    def spawn_ready(self, code: str, species_code: str) -> None:
        crud.update_bag_ready(self.db, code)
        self.ready_spawn[species_code].append(code)

    # ------------------------------------------------------------- substrate

    def pasteurization_run(self, bad: bool) -> None:
        db = self.db
        day = self.day_of(self.now)
        bag_count = self.rng.randint(32, 48)
        run_code = bag_id.next_run_code(db, models.PasteurizationRun, day)
        recipe_id = self.rng.choice(self.reference["substrate_recipe_ids"])
        mix_lot = crud.create_mix_lot(
            db,
            {
                "lot_code": f"MIX-{run_code}",
                "substrate_recipe_version_id": recipe_id,
                "fill_profile_id": self.reference["fill_profile_id"],
                "mixed_at": self.local(day, 7, 30),
                "notes": DEMO_NOTE,
            },
        )
        run = crud.create_pasteurization_run(
            db,
            {
                "run_code": run_code,
                "mix_lot_id": mix_lot.mix_lot_id,
                "substrate_recipe_version_id": recipe_id,
                "steam_start_at": self.local(day, 9, 0),
                "steam_end_at": self.local(day, 13, 0),
                "unloaded_at": self.now,
                "bag_count": bag_count,
                "notes": DEMO_NOTE,
            },
        )
        self.counts["pasteurization_runs"] += 1
        if bad:
            self.bad_run_code = run_code
        self.tick(300)
        crud.create_substrate_bags(db, run.pasteurization_run_id, bag_count)
        self.counts["bag_records"] += bag_count
        self.counts["substrate_bag_records"] += bag_count
        run_id = run.pasteurization_run_id
        self.at(
            self.local(day + timedelta(days=1), 10, 0) + timedelta(minutes=self.rng.randrange(0, 45, 5)),
            lambda: self.inoculate_substrate(run_id, run_code, bag_count, bad),
        )

    def inoculate_substrate(self, run_id: int, run_code: str, bag_count: int, bad: bool) -> None:
        varieties = self.pick_species(self.rng.choices((1, 2, 3), weights=(35, 45, 20))[0])
        for species, size in zip(varieties, self.split(bag_count, len(varieties), 6)):
            remaining = size
            own = self.ready_spawn[species.code]
            if own and self.rng.random() < OWN_SPAWN_SHARE:
                # One of the farm's spawn bags does eight to twelve substrate bags, then it is spent.
                while remaining and own:
                    spawn_code = own.popleft()
                    take = min(remaining, self.rng.randint(8, 12))
                    bags = crud.create_inoculation_batch(self.db, run_id, take, spawn_bag_id=spawn_code)
                    self.after_substrate_session(bags, species, run_code, "SPAWN_BAG", spawn_code, bad)
                    remaining -= take
            if remaining:
                lot_id, lot_code = self.lot_for(species)
                bags = crud.create_inoculation_batch(self.db, run_id, remaining, purchased_spawn_lot_id=lot_id)
                self.after_substrate_session(bags, species, run_code, "PURCHASED_SPAWN", lot_code, bad)

    def after_substrate_session(self, bags, species: _Species, run_code: str, source_type: str, source_code: str, bad: bool) -> None:
        codes = [bag.bag_code for bag in bags]
        dry_kg = self.reference["fill_dry_kg"]
        for code in codes:
            self.ledger[code] = LedgerEntry(
                "SUBSTRATE", code, species.code, run_code, source_type, source_code, dry_kg=dry_kg
            )
        self.start_incubation(codes)
        self.plan_substrate_bags(codes, species, dry_kg, bad)
        self.tick(600)

    def weigh(self, kg: float) -> float:
        """To the nearest five grams, as a kitchen scale reads."""
        return max(0.05, round(round(kg / 0.005) * 0.005, 3))

    def plan_substrate_bags(self, codes: list[str], species: _Species, dry_kg: float, bad: bool) -> None:
        """Decide what becomes of each bag of a session, and put it in the diary."""
        rng = self.rng
        inoculated = self.day_of(self.now)
        contamination = BAD_RUN_CONTAMINATION if bad else BASE_CONTAMINATION

        # A session's bags move together; a few lag a day or three behind.
        ready_day = inoculated + timedelta(days=rng.randint(*species.colonization_days))
        fruiting_gap = rng.randint(0, 2)
        to_first_flush = rng.randint(4, 7) + rng.randint(*species.pin_to_harvest_days)
        ready_time, fruiting_time, harvest_time, second_time = (self.work_moment() for _ in range(4))

        for index, code in enumerate(codes):
            offset = timedelta(seconds=20 * index)
            if rng.random() < contamination:
                found = inoculated + timedelta(days=rng.randint(5, 14))
                self.at(self.local(found, *ready_time) + offset, lambda code=code: self.dispose(code, "CONTAMINATION"))
                continue

            lag = 0 if rng.random() < 0.8 else rng.randint(1, 3)
            ready = ready_day + timedelta(days=lag)
            fruiting = ready + timedelta(days=fruiting_gap)
            first = fruiting + timedelta(days=to_first_flush + rng.randint(0, 2))

            efficiency = rng.uniform(*species.efficiency_pct) / 100 * rng.uniform(0.85, 1.15)
            two_flushes = FLUSH_LIMIT >= 2 and rng.random() < SECOND_FLUSH_SHARE
            first_share = rng.uniform(0.62, 0.75) if two_flushes else rng.uniform(0.7, 0.9)
            first_kg = self.weigh(dry_kg * efficiency * first_share)
            second_kg = self.weigh(dry_kg * efficiency * (1 - first_share))
            late_contamination = rng.random() < LATE_CONTAMINATION
            second = first + timedelta(days=rng.randint(10, 16))
            cleared_after = rng.randint(1, 4)
            found_after = rng.randint(3, 8)

            ready_at = self.local(ready, *ready_time) + offset
            # Moved to the fruiting room the same day or up to two days later, never before it was ready.
            fruiting_at = max(self.local(fruiting, *fruiting_time) + offset, ready_at + timedelta(minutes=30))
            self.at(ready_at, lambda code=code: crud.update_bag_ready(self.db, code))
            self.at(fruiting_at, lambda code=code: crud.update_bag_fruiting_start(self.db, code))
            self.at(
                self.local(first, *harvest_time) + offset,
                lambda code=code, kg=first_kg: self.harvest(code, 1, kg),
            )
            if late_contamination:
                self.at(
                    self.local(first + timedelta(days=found_after), *second_time) + offset,
                    lambda code=code: self.dispose(code, "CONTAMINATION"),
                )
                continue
            last = first
            if two_flushes:
                self.at(
                    self.local(second, *second_time) + offset,
                    lambda code=code, kg=second_kg: self.harvest(code, 2, kg),
                )
                last = second
            self.at(
                self.local(last + timedelta(days=cleared_after), *second_time) + offset + timedelta(minutes=45),
                lambda code=code: self.dispose(code, "FINAL_HARVEST"),
            )

    # ---------------------------------------------------------------- events

    def harvest(self, code: str, flush: int, kg: float) -> None:
        crud.create_harvest_event(self.db, code, flush, kg)
        self.ledger[code].harvests_kg.append(kg)
        self.counts["harvest_events"] += 1

    def dispose(self, code: str, reason: str) -> None:
        crud.update_bag_disposal(self.db, code, reason)
        if reason == "CONTAMINATION":
            self.ledger[code].contaminated = True


def generate(
    db: Session,
    config: DemoConfig = DemoConfig(),
    *,
    allow_existing_data: bool = False,
    allow_production: bool = False,
    user_email: str | None = None,
) -> DemoResult:
    """Write a demo farm to `db` and say what was written."""
    config.validate()
    _check_allowed(db, allow_existing_data=allow_existing_data, allow_production=allow_production)

    previous_user = db.info.get("user_id")
    if user_email:
        user = db.execute(select(models.User).where(models.User.email == user_email.strip().lower())).scalars().first()
        if user is None:
            raise DemoDataRefused(f"No user has the email {user_email}.")
        db.info["user_id"] = user.user_id

    simulation = _Simulation(db, config)
    try:
        with clock.simulated(lambda: simulation.now):
            simulation.set_up()
        simulation.plan()
        simulation.run()
    finally:
        if previous_user is None:
            db.info.pop("user_id", None)
        else:
            db.info["user_id"] = previous_user

    counts = {
        key: simulation.counts.get(key, 0)
        for key in (
            "sterilization_runs",
            "pasteurization_runs",
            "purchased_spawn_lots",
            "liquid_cultures",
            "bag_records",
            "spawn_bag_records",
            "substrate_bag_records",
            "harvest_events",
        )
    }
    return DemoResult(
        config=config,
        first_day=simulation.first_day,
        last_day=simulation.last_day,
        ledger=simulation.ledger,
        bad_run_code=simulation.bad_run_code,
        counts=counts,
        fill_dry_kg=simulation.reference["fill_dry_kg"],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.seed_demo",
        description="Fill an empty database with a realistic, repeatable demo farm.",
    )
    parser.add_argument("--seed", type=int, default=1, help="the same seed gives the same farm (default 1)")
    parser.add_argument("--scale", type=float, default=1.0, help="1 is the farm's own volume, about 1,000 bags in twelve weeks; 10 gives about 10,000")
    parser.add_argument("--weeks", type=int, default=12, help="how many weeks of work to record (default 12)")
    parser.add_argument("--end-date", type=date.fromisoformat, default=None, help="last day of the story, YYYY-MM-DD (default yesterday)")
    parser.add_argument("--user", default=None, help="email of an existing user to record the work under")
    parser.add_argument("--allow-existing-data", action="store_true", help="add to a database that already holds runs, bags, lots or cultures")
    parser.add_argument("--allow-production", action="store_true", help="run even though APP_ENV is production")
    args = parser.parse_args(argv)

    config = DemoConfig(seed=args.seed, scale=args.scale, weeks=args.weeks, end_date=args.end_date)
    db = SessionLocal()
    try:
        result = generate(
            db,
            config,
            allow_existing_data=args.allow_existing_data,
            allow_production=args.allow_production,
            user_email=args.user,
        )
    except (DemoDataRefused, ValueError) as refusal:
        print(f"Refused: {refusal}", file=sys.stderr)
        return 2
    finally:
        db.close()
    print("\n".join(result.lines()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
