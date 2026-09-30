

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()
SessionLocal = sessionmaker()

_engin: Engine | None = None


def get_engine() -> Engine:
    ...


def new_session() -> Session:
    ...


def get_db():
    ...
    