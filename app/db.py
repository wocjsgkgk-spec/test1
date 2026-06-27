from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.models.user import User
from app.orm_base import Base
from app.orm_models import TodoRecord

_DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "todos.db"


def _sqlite_url(path: str | Path) -> str:
    return URL.create("sqlite", database=str(Path(path))).render_as_string(
        hide_password=False
    )


def database_url_from_environment() -> str:
    if database_url := os.getenv("DATABASE_URL"):
        return database_url
    if database_path := os.getenv("TODO_DB_PATH"):
        return _sqlite_url(database_path)
    return _sqlite_url(_DEFAULT_DATABASE_PATH)


def _create_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    options: dict[str, object] = {}
    if url.get_backend_name() == "sqlite":
        options["connect_args"] = {"check_same_thread": False}

    engine = create_engine(database_url, **options)
    if url.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _create_engine(database_url_from_environment())
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def configure_database_url(database_url: str) -> None:
    """DB URL을 적용하고, 개발 및 테스트용 스키마를 생성한다."""
    global engine, SessionLocal
    engine.dispose()
    engine = _create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    initialize_database()


def configure_database(path: str | Path) -> None:
    """기존 테스트와 SQLite 배포 설정을 위한 호환 함수."""
    configure_database_url(_sqlite_url(path))


async def get_session() -> AsyncGenerator[Session, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)


def reset_store() -> None:
    with SessionLocal.begin() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
