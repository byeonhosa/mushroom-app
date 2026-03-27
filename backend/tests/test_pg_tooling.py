from datetime import datetime
from pathlib import Path

import pytest

from app.pg_tooling import (
    build_createdb_command,
    build_dropdb_command,
    build_pg_dump_command,
    build_pg_env,
    build_pg_restore_command,
    default_backup_path,
    parse_postgres_connection,
)


def test_parse_postgres_connection_supports_psycopg_url():
    info = parse_postgres_connection("postgresql+psycopg://mushroom:secret@db.internal:5433/mushroom")

    assert info.host == "db.internal"
    assert info.port == 5433
    assert info.user == "mushroom"
    assert info.password == "secret"
    assert info.database == "mushroom"


def test_parse_postgres_connection_rejects_non_postgres_urls():
    with pytest.raises(ValueError):
        parse_postgres_connection("sqlite:///./test.db")


def test_backup_and_restore_commands_are_built_consistently():
    output_path = Path("backups/mushroom_20260326_120000.dump")
    input_path = Path("backups/seed.dump")

    assert build_pg_dump_command(output_path) == [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        f"--file={output_path}",
    ]
    assert build_dropdb_command("mushroom") == ["dropdb", "--if-exists", "mushroom"]
    assert build_createdb_command("mushroom") == ["createdb", "mushroom"]
    assert build_pg_restore_command(input_path, "mushroom") == [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "--dbname=mushroom",
        str(input_path),
    ]


def test_backup_path_uses_timestamped_dump_name():
    output_path = default_backup_path(Path("backups"), now=datetime(2026, 3, 26, 12, 30, 45))

    assert output_path == Path("backups/mushroom_20260326_123045.dump")


def test_pg_env_includes_password_when_present():
    info = parse_postgres_connection("postgresql://mushroom:secret@localhost:5432/mushroom")

    assert build_pg_env(info) == {
        "PGHOST": "localhost",
        "PGPORT": "5432",
        "PGUSER": "mushroom",
        "PGPASSWORD": "secret",
        "PGDATABASE": "mushroom",
    }
