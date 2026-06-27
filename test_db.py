from pathlib import Path

from sqlalchemy import inspect

from app import db


def test_database_url_prefers_database_url(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db/taskflow")
    monkeypatch.setenv("TODO_DB_PATH", "ignored.db")

    assert db.database_url_from_environment() == (
        "postgresql+psycopg://user:pass@db/taskflow"
    )


def test_database_url_uses_psycopg_driver_for_plain_postgresql_url(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:pass@db/taskflow?sslmode=require",
    )

    assert db.database_url_from_environment() == (
        "postgresql+psycopg://user:pass@db/taskflow?sslmode=require"
    )


def test_configure_database_keeps_sqlite_path_compatibility(tmp_path: Path) -> None:
    database_path = tmp_path / "compatibility.db"

    db.configure_database(database_path)

    assert db.engine.url.get_backend_name() == "sqlite"
    assert set(inspect(db.engine).get_table_names()) == {
        "todos",
        "users",
    }
