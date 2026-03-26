import os
import re
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.migrate import MIG_DIR, apply_migration, applied, ensure_schema_migrations


def _database_url() -> str:
    return os.environ["DATABASE_URL"]


def _is_postgres_url(url: str) -> bool:
    return make_url(url).get_backend_name() == "postgresql"


def _temp_database_name() -> str:
    return f"mushroom_migration_{uuid.uuid4().hex[:10]}"


def _quoted_db_identifier(name: str) -> str:
    assert re.fullmatch(r"[a-z0-9_]+", name)
    return name


def test_postgres_migrations_apply_cleanly():
    database_url = _database_url()
    if not _is_postgres_url(database_url):
        pytest.skip("Migration smoke test requires PostgreSQL.")

    base_url = make_url(database_url)
    temp_database = _quoted_db_identifier(_temp_database_name())
    admin_engine = create_engine(
        base_url.set(database="postgres").render_as_string(hide_password=False),
        isolation_level="AUTOCOMMIT",
        pool_pre_ping=True,
    )
    temp_engine = None

    try:
        with admin_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE {temp_database}"))

        temp_engine = create_engine(
            base_url.set(database=temp_database).render_as_string(hide_password=False),
            pool_pre_ping=True,
        )
        ensure_schema_migrations(temp_engine)

        migration_files = sorted(MIG_DIR.glob("*.sql"))
        for migration_file in migration_files:
            if migration_file.name in applied(temp_engine):
                continue
            apply_migration(temp_engine, migration_file.name, migration_file.read_text(encoding="utf-8"))

        with temp_engine.begin() as conn:
            applied_filenames = conn.execute(
                text("SELECT filename FROM schema_migrations ORDER BY filename")
            ).scalars().all()

        tables = set(inspect(temp_engine).get_table_names())

        assert applied_filenames == [migration_file.name for migration_file in migration_files]
        assert {
            "bag_status_events",
            "bags",
            "grain_types",
            "harvest_events",
            "ingredient_lots",
            "ingredients",
            "inoculations",
            "mushroom_species",
            "pasteurization_runs",
            "sterilization_runs",
        } <= tables
    finally:
        if temp_engine is not None:
            temp_engine.dispose()
        with admin_engine.connect() as conn:
            conn.execute(
                text(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = :database_name
                      AND pid <> pg_backend_pid()
                    """
                ),
                {"database_name": temp_database},
            )
            conn.execute(text(f"DROP DATABASE IF EXISTS {temp_database}"))
        admin_engine.dispose()
