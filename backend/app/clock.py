"""The clock the farm records are stamped with.

Every "now" written to a run, a bag or an event comes through `now()`. In the
running app that is the real time. The demo data generator (`app.seed_demo`)
replaces it for the length of a simulation, so that twelve weeks of work can
be recorded through the same code an operator's taps go through, each step
stamped with the moment it would have happened.

Sign-in does not use this clock: sessions and rate limits always run on real
time (`app.auth`).
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Callable, Iterator

_source: ContextVar[Callable[[], datetime] | None] = ContextVar("clock_source", default=None)


def now() -> datetime:
    source = _source.get()
    if source is None:
        return datetime.now(timezone.utc)
    moment = source()
    if moment.tzinfo is None:
        raise ValueError("A simulated clock must return a time with an offset.")
    return moment.astimezone(timezone.utc)


@contextmanager
def simulated(source: Callable[[], datetime]) -> Iterator[None]:
    """Within the block, `now()` returns whatever `source()` returns."""
    token = _source.set(source)
    try:
        yield
    finally:
        _source.reset(token)
