"""Errors the API turns into plain messages, and driver-independent checks."""
from sqlalchemy.exc import IntegrityError


class DomainError(ValueError):
    """A request that breaks a rule of the data. Answered with 400."""

    status_code = 400


class NotFoundError(DomainError, LookupError):
    """The record the request names does not exist. Answered with 404."""

    status_code = 404


class ConflictError(DomainError):
    """The request collides with a record that already exists. Answered with 409."""

    status_code = 409


def is_unique_violation(exc: IntegrityError) -> bool:
    """True when an IntegrityError is a duplicate key, on PostgreSQL or SQLite.

    PostgreSQL reports SQLSTATE 23505 through whichever driver is in use;
    SQLite reports it only in the message text.
    """
    orig = getattr(exc, "orig", None)
    if getattr(orig, "sqlstate", None) == "23505":
        return True
    return "unique constraint failed" in str(orig).lower()
