from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from internly.config import settings


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_parent_exists(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    raw_path = database_url.replace("sqlite:///", "", 1)
    if raw_path == ":memory:":
        return
    Path(raw_path).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_exists(settings.database_url)

# Setup engine with 30s timeout for SQLite to prevent locking issues
connect_args = {"timeout": 30} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,
    future=True,
    connect_args=connect_args,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    from internly.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    from internly.db import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)

