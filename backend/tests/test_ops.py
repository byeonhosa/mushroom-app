from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app import models, ops
from app.main import app
from app.migrate import ensure_schema_migrations, MIG_DIR


def _sqlite_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_live_health_reports_service_metadata():
    payload = ops.get_live_health()

    assert payload["ok"] is True
    assert payload["service"] == "Mushroom Farm App API"
    assert payload["version"] == "0.1.0"
    assert payload["environment"]


def test_readiness_reports_missing_migrations_for_unprepared_database():
    engine = _sqlite_engine()
    models.Base.metadata.create_all(bind=engine)

    payload = ops.get_readiness_health(engine)
    checks = {check["name"]: check for check in payload["checks"]}

    assert payload["ok"] is False
    assert payload["database_backend"] == "sqlite"
    assert checks["database_connection"]["ok"] is True
    assert checks["schema_migrations"]["ok"] is False
    assert len(payload["pending_migrations"]) == len(list(MIG_DIR.glob("*.sql")))


def test_readiness_is_ok_when_core_tables_and_migrations_are_present():
    engine = _sqlite_engine()
    models.Base.metadata.create_all(bind=engine)
    ensure_schema_migrations(engine)

    with engine.begin() as conn:
        for migration_file in sorted(MIG_DIR.glob("*.sql")):
            conn.execute(
                text("INSERT INTO schema_migrations(filename) VALUES (:filename)"),
                {"filename": migration_file.name},
            )

    payload = ops.get_readiness_health(engine)
    checks = {check["name"]: check for check in payload["checks"]}

    assert payload["ok"] is True
    assert payload["pending_migrations"] == []
    assert checks["schema_migrations"]["ok"] is True
    assert checks["pending_migrations"]["ok"] is True
    assert checks["core_tables"]["ok"] is True


def test_ready_endpoint_returns_service_unavailable_when_not_ready(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(
        "app.api.ops.get_readiness_health",
        lambda: {
            "ok": False,
            "service": "Mushroom Farm App API",
            "version": "0.1.0",
            "environment": "test",
            "checked_at": "2026-03-26T00:00:00Z",
            "database_backend": "sqlite",
            "pending_migrations": ["001_init.sql"],
            "checks": [],
        },
    )

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["ok"] is False
