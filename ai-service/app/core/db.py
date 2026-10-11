

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import DATABASE_URL

Base = declarative_base()
SessionLocal = sessionmaker()

_engin: Engine | None = None


def get_engine() -> Engine:
    global _engin
    if _engin is None:
        _engin = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engin


def new_session() -> Session:
    ...


def get_db():
    ...
    