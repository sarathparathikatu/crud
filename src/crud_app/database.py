"""Database setup: one engine for the app and a per-request session dependency."""

import os
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

# Read the location from an environment variable so the same code can point at a
# local file, a Docker volume, or a real Postgres server without changes.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

# SQLite only: FastAPI may hand a connection to a different thread than the one
# that opened it, which SQLite refuses unless check_same_thread is False.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)


def create_db_and_tables() -> None:
    """Create every table defined with `table=True` (no-op if they already exist)."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: open one session per request and always close it.

    Tests replace this function with one that returns an in-memory database
    session (see tests/conftest.py).
    """
    with Session(engine) as session:
        yield session
