# [역할] DB 연결 — SQLAlchemy 엔진·세션을 만들고, 요청마다 세션을 열고 닫는 get_db 의존성을 제공한다.
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 제너레이터(yield) 함수의 반환 타입.
from collections.abc import Iterator

# Engine: DB 연결 풀, create_engine: 엔진 생성 함수.
from sqlalchemy import Engine, create_engine
# Session: DB 작업 단위, declarative_base: ORM 모델 기반 클래스, sessionmaker: 세션 공장.
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# DATABASE_URL·풀 크기 등 설정값.
from app.core import config

# ORM 모델을 만들 때 상속할 기반 클래스(지금은 Core 테이블만 쓰지만 기존 골격 유지).
Base = declarative_base()
# 세션을 찍어 내는 공장. 엔진은 나중에 bind 한다. commit 후에도 객체 값을 유지한다.
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)

# 프로세스 전체에서 하나만 쓰는 엔진. 처음엔 비어 있다.
_engine: Engine | None = None


# 엔진을 돌려준다. 없으면 이때 처음 만든다.
def get_engine() -> Engine:
    """엔진은 프로세스당 하나. 첫 호출 때 만든다 — import 만으로 DB 에 붙지 않게."""
    # 모듈 전역 변수 _engine 을 바꾸겠다고 선언한다.
    global _engine
    # 아직 엔진이 없으면
    if _engine is None:
        # DB 주소가 설정돼 있지 않으면
        if not config.DATABASE_URL:
            # 설정을 확인하라고 알린다.
            raise RuntimeError("DATABASE_URL 이 비어 있습니다. ai-service/.env 를 확인하세요.")
        # 연결 풀을 가진 엔진을 만든다.
        _engine = create_engine(
            # 접속 주소
            config.DATABASE_URL,
            # 평소 유지할 연결 수
            pool_size=config.DB_POOL_SIZE,
            # 바쁠 때 추가로 열 수 있는 연결 수
            max_overflow=config.DB_MAX_OVERFLOW,
            # 연결을 꺼내 쓰기 전에 살아 있는지 확인한다.
            pool_pre_ping=True,  # Supabase 풀러가 유휴 연결을 끊는다
        )
        # 세션 공장이 이 엔진을 쓰도록 연결한다.
        SessionLocal.configure(bind=_engine)
    # 엔진을 돌려준다.
    return _engine


# 새 세션 하나를 만든다.
def new_session() -> Session:
    # 엔진이 준비돼 있는지 확인(없으면 생성)한다.
    get_engine()
    # 세션 공장으로 세션을 만들어 돌려준다.
    return SessionLocal()


# FastAPI 의존성: 요청이 들어오면 세션을 열고, 응답 후 닫는다.
def get_db() -> Iterator[Session]:
    """FastAPI 의존성. 요청 하나에 세션 하나, 끝나면 닫는다."""
    # 세션을 연다.
    session = new_session()
    # 라우트 실행 중 오류가 나도 반드시 닫도록 try 로 감싼다.
    try:
        # 라우트에 세션을 넘겨준다(라우트가 끝날 때까지 여기서 대기).
        yield session
    # 성공·실패와 상관없이
    finally:
        # 세션을 닫아 연결을 풀에 돌려준다.
        session.close()
