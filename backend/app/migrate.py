from pathlib import Path
from sqlalchemy import create_engine, text
from .config import settings

MIG_DIR = Path(__file__).parent / "migrations"

def ensure_schema_migrations(engine):
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
          id SERIAL PRIMARY KEY,
          filename TEXT NOT NULL UNIQUE,
          applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """))

def applied(engine) -> set[str]:
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT filename FROM schema_migrations")).fetchall()
        return {r[0] for r in rows}

def apply_migration(engine, filename: str, sql: str):
    with engine.begin() as conn:
        conn.execute(text(sql))
        conn.execute(text("INSERT INTO schema_migrations(filename) VALUES (:f)"), {"f": filename})

def main():
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    ensure_schema_migrations(engine)
    done = applied(engine)

    files = sorted([p for p in MIG_DIR.glob("*.sql")])
    for p in files:
        if p.name in done:
            continue
        sql = p.read_text(encoding="utf-8")
        apply_migration(engine, p.name, sql)
        print(f"Applied {p.name}")

if __name__ == "__main__":
    main()
