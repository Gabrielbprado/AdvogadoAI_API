"""SQLite database setup and session helpers."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Declarative base class for SQLAlchemy models."""


_engine_cache = {}


def get_engine(database_url: str) -> object:
    """Return a cached SQLAlchemy engine for the given URL."""
    engine = _engine_cache.get(database_url)
    if engine is None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        engine = create_engine(database_url, connect_args=connect_args)
        _engine_cache[database_url] = engine
    return engine


def build_session_factory(database_url: str):
    """Create a sessionmaker bound to the configured engine."""
    engine = get_engine(database_url)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_all(database_url: str, base: type[Base], storage_dir: Path) -> None:
    """Create database tables if they do not exist."""
    storage_dir.mkdir(parents=True, exist_ok=True)
    if database_url.startswith("sqlite:///"):
        db_path = Path(database_url.replace("sqlite:///", "", 1))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = get_engine(database_url)
    base.metadata.create_all(bind=engine)


@contextmanager
def session_scope(session_factory) -> Iterator:
    """Provide a transactional scope around a series of operations."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
