from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core import config

Base = declarative_base()
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)

_engine: Engine | None = None


def get_engine() -> Engine:
    """엔진은 프로세스당 하나. 첫 호출 때 만든다 — import 만으로 DB 에 붙지 않게."""
    global _engine
    if _engine is None:
        if not config.DATABASE_URL:
            raise RuntimeError("DATABASE_URL 이 비어 있습니다. ai-service/.env 를 확인하세요.")
        _engine = create_engine(
            config.DATABASE_URL,
            pool_size=config.DB_POOL_SIZE,
            max_overflow=config.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
        )
        SessionLocal.configure(bind=_engine)
    return _engine


def new_session() -> Session:
    get_engine()
    return SessionLocal()


def get_db() -> Iterator[Session]:
    """FastAPI 의존성. 요청 하나에 세션 하나, 끝나면 닫는다."""
    session = new_session()
    try:
        yield session
    finally:
        session.close()
