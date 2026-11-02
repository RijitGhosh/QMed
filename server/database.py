"""SQLAlchemy engine/session management (PostgreSQL-compatible models)."""
from __future__ import annotations

from typing import Optional

from flask import current_app, g
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


class Database:
    def __init__(self, url: str):
        kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(url, future=True, **kwargs)
        if url.startswith("sqlite"):
            @event.listens_for(self.engine, "connect")
            def _fk_on(dbapi_conn, _):  # enforce foreign keys in SQLite
                dbapi_conn.execute("PRAGMA foreign_keys=ON")
        self._factory = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def session(self) -> Session:
        return self._factory()


def get_db() -> Session:
    """Per-request database session (closed automatically at teardown)."""
    if "db" not in g:
        g.db = current_app.extensions["qmed_db"].session()
    return g.db


def close_db(_exc: Optional[BaseException] = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()
