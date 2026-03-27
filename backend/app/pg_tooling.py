from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import make_url


@dataclass(frozen=True)
class PostgresConnectionInfo:
    host: str
    port: int
    user: str
    password: str | None
    database: str


def parse_postgres_connection(database_url: str) -> PostgresConnectionInfo:
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql":
        raise ValueError("PostgreSQL tooling requires a postgresql DATABASE_URL.")
    if not url.host or not url.username or not url.database:
        raise ValueError("DATABASE_URL must include host, username, and database name.")

    return PostgresConnectionInfo(
        host=url.host,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        database=url.database,
    )


def build_pg_env(info: PostgresConnectionInfo) -> dict[str, str]:
    env = {
        "PGHOST": info.host,
        "PGPORT": str(info.port),
        "PGUSER": info.user,
        "PGDATABASE": info.database,
    }
    if info.password:
        env["PGPASSWORD"] = info.password
    return env


def default_backup_path(output_dir: Path, *, now: datetime | None = None) -> Path:
    now = now or datetime.utcnow()
    filename = f"mushroom_{now.strftime('%Y%m%d_%H%M%S')}.dump"
    return output_dir / filename


def build_pg_dump_command(output_path: Path) -> list[str]:
    return [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        f"--file={output_path}",
    ]


def build_dropdb_command(database_name: str) -> list[str]:
    return [
        "dropdb",
        "--if-exists",
        database_name,
    ]


def build_createdb_command(database_name: str) -> list[str]:
    return [
        "createdb",
        database_name,
    ]


def build_pg_restore_command(input_path: Path, database_name: str) -> list[str]:
    return [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        f"--dbname={database_name}",
        str(input_path),
    ]
