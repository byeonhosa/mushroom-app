import argparse
import os
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.pg_tooling import (  # noqa: E402
    build_createdb_command,
    build_dropdb_command,
    build_pg_env,
    build_pg_restore_command,
    parse_postgres_connection,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Restore a PostgreSQL backup for the mushroom app.")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="Target PostgreSQL DATABASE_URL. Defaults to DATABASE_URL from the environment.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the .dump backup file produced by postgres_backup.py.",
    )
    parser.add_argument(
        "--skip-drop-create",
        action="store_true",
        help="Restore into the existing database without dropping and recreating it first.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required.")
    if not args.input.exists():
        raise SystemExit(f"Backup file not found: {args.input}")

    connection = parse_postgres_connection(args.database_url)
    env = {**os.environ, **build_pg_env(connection)}

    if not args.skip_drop_create:
        subprocess.run(build_dropdb_command(connection.database), check=True, env=env)
        subprocess.run(build_createdb_command(connection.database), check=True, env=env)

    subprocess.run(build_pg_restore_command(args.input, connection.database), check=True, env=env)
    print(f"Restored {args.input} into {connection.database}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
