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
    _migrate_db()


def _migrate_db() -> None:
    """Additive schema migrations for existing databases (safe to run on every startup)."""
    from sqlalchemy import text

    migrations = [
        "ALTER TABLE evaluations ADD COLUMN question_breakdown JSON DEFAULT '[]'",
        "ALTER TABLE candidates ADD COLUMN job_description TEXT",
        "ALTER TABLE candidates ADD COLUMN target_languages JSON DEFAULT '[]'",
        "ALTER TABLE candidates ADD COLUMN alignment_signals JSON DEFAULT '[]'",
        "ALTER TABLE candidates ADD COLUMN skill_gaps JSON DEFAULT '[]'",
        "ALTER TABLE company_intel ADD COLUMN interview_playbook_text TEXT",
        "ALTER TABLE candidates ADD COLUMN name VARCHAR(255) DEFAULT ''",
        "ALTER TABLE candidates ADD COLUMN achievements JSON DEFAULT '[]'",
    ]
    with engine.connect() as conn:
        for stmt in migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass  # column already exists — safe to ignore


def drop_db() -> None:
    from internly.db import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)

