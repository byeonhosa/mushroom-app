from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .db import engine
from .migrate import MIG_DIR, applied

_CORE_TABLES = {
    "bag_status_events",
    "bags",
    "harvest_events",
    "inoculation_batches",
    "mushroom_species",
    "pasteurization_runs",
    "schema_migrations",
    "sterilization_runs",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expected_migration_filenames() -> list[str]:
    return [migration_file.name for migration_file in sorted(MIG_DIR.glob("*.sql"))]


def _pending_migration_filenames(runtime_engine: Engine) -> list[str]:
    return [
        filename
        for filename in _expected_migration_filenames()
        if filename not in applied(runtime_engine)
    ]


def get_live_health() -> dict:
    return {
        "ok": True,
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "checked_at": _now(),
    }


def get_readiness_health(runtime_engine: Engine | None = None) -> dict:
    runtime_engine = runtime_engine or engine
    payload = get_live_health()
    payload["database_backend"] = runtime_engine.url.get_backend_name()
    payload["pending_migrations"] = []
    payload["checks"] = []

    try:
        with runtime_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        payload["checks"].append(
            {
                "name": "database_connection",
                "ok": True,
                "detail": "Database connection succeeded.",
            }
        )
    except SQLAlchemyError as exc:
        payload["ok"] = False
        payload["checks"].append(
            {
                "name": "database_connection",
                "ok": False,
                "detail": f"Database connection failed: {exc.__class__.__name__}.",
            }
        )
        return payload

    inspector = inspect(runtime_engine)
    table_names = set(inspector.get_table_names())
    if "schema_migrations" not in table_names:
        pending = _expected_migration_filenames()
        payload["ok"] = False
        payload["pending_migrations"] = pending
        payload["checks"].append(
            {
                "name": "schema_migrations",
                "ok": False,
                "detail": "schema_migrations table is missing.",
            }
        )
    else:
        payload["checks"].append(
            {
                "name": "schema_migrations",
                "ok": True,
                "detail": "schema_migrations table is present.",
            }
        )
        try:
            pending = _pending_migration_filenames(runtime_engine)
        except SQLAlchemyError as exc:
            payload["ok"] = False
            payload["checks"].append(
                {
                    "name": "pending_migrations",
                    "ok": False,
                    "detail": f"Unable to inspect applied migrations: {exc.__class__.__name__}.",
                }
            )
        else:
            payload["pending_migrations"] = pending
            payload["checks"].append(
                {
                    "name": "pending_migrations",
                    "ok": not pending,
                    "detail": (
                        "All migrations are applied."
                        if not pending
                        else f"{len(pending)} migration(s) pending."
                    ),
                }
            )
            if pending:
                payload["ok"] = False

    missing_tables = sorted(_CORE_TABLES - table_names)
    payload["checks"].append(
        {
            "name": "core_tables",
            "ok": not missing_tables,
            "detail": (
                "Required tables are present."
                if not missing_tables
                else f"Missing required tables: {', '.join(missing_tables)}."
            ),
        }
    )
    if missing_tables:
        payload["ok"] = False

    return payload
