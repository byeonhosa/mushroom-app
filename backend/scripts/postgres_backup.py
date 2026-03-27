import argparse
import os
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.pg_tooling import build_pg_dump_command, build_pg_env, default_backup_path, parse_postgres_connection  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a PostgreSQL backup for the mushroom app.")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL DATABASE_URL. Defaults to DATABASE_URL from the environment.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for the backup file. Defaults to backups/mushroom_YYYYMMDD_HHMMSS.dump.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required.")

    connection = parse_postgres_connection(args.database_url)
    output_path = args.output or default_backup_path(BACKEND_DIR.parent / "backups")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, **build_pg_env(connection)}
    command = build_pg_dump_command(output_path)
    subprocess.run(command, check=True, env=env)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
