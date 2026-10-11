# [역할] 상권 조회 라우트 — GET /api/market/regions·dongs·cells·trends·industries 5종 (F-MAP-01~06).
"""GET /api/market/* — 상권 '신호등'(F-MAP-01~05). 공통 필터는 F-MAP-06."""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 타입에 부가정보(Query·Depends 등)를 붙이는 도구.
from typing import Annotated

# APIRouter: 라우트 묶음, Depends: 의존성, Path: 경로 변수, Query: 쿼리 파라미터.
from fastapi import APIRouter, Depends, Path, Query
# DB 세션 타입.
from sqlalchemy.orm import Session

# 요청마다 DB 세션을 주는 의존성.
from app.core.db import get_db
# 목록 응답 틀과 공통 필터 모델.
from app.schemas.common import ListResponse, MarketFilter
# 상권 응답·쿼리 모델들.
from app.schemas.market import (
    # /cells 쿼리(공통 필터 + 행정동 코드)
    CellQuery,
    # /cells 응답
    CellResponse,
    # /dongs 항목
    DongItem,
    # /industries 항목
    IndustryRankItem,
    # /industries 쿼리(공통 필터 + 정렬·개수)
    IndustryRankQuery,
    # /regions 항목
    RegionItem,
    # /trends 응답
    TrendResponse,
)
# 실제 로직을 담당하는 상권 서비스.
from app.service import market_service

# /api/market 으로 시작하는 라우트 묶음. 문서에서 'market' 태그로 묶인다.
router = APIRouter(prefix="/api/market", tags=["market"])

# 공통 필터를 쿼리스트링 전체에서 읽어 MarketFilter 로 만든다는 타입 별칭.
Filter = Annotated[MarketFilter, Query()]
# DB 세션을 주입받는다는 타입 별칭.
DB = Annotated[Session, Depends(get_db)]


# GET /api/market/regions — 자치구×산업 위험도 지도 데이터.
@router.get("/regions", response_model=ListResponse[RegionItem], summary="자치구 위험도 지도 (F-MAP-01)")
def regions(f: Filter, db: DB):
    # 서비스에 위임해 결과를 돌려준다.
    return market_service.get_regions(db, f)


# GET /api/market/regions/{gu}/dongs — 자치구 클릭 시 행정동×산업 성적표.
@router.get("/regions/{gu}/dongs", response_model=ListResponse[DongItem], summary="행정동 드릴다운 (F-MAP-02)")
def dongs(gu: Annotated[str, Path(description="자치구명", examples=["마포구"])], f: Filter, db: DB):
    # 경로의 자치구명과 필터를 서비스에 넘긴다.
    return market_service.get_dongs(db, gu, f)


# GET /api/market/cells — 행정동×업종 분기별 시계열 상세.
@router.get("/cells", response_model=CellResponse, summary="행정동×업종 상세 카드 (F-MAP-03)")
def cells(q: Annotated[CellQuery, Query()], db: DB):
    # 업종은 공통 필터의 industry_code 를 쓴다(필수). 없으면 서비스가 422.
    return market_service.get_cells(db, q.district_code, q)


# GET /api/market/trends — 분기별 산업 추이와 역전 구간.
@router.get("/trends", response_model=TrendResponse, summary="분기별 산업 추이 (F-MAP-04)")
def trends(f: Filter, db: DB):
    # 서비스에 위임한다.
    return market_service.get_trends(db, f)


# GET /api/market/industries — 업종별 폐업률 순위.
@router.get("/industries", response_model=ListResponse[IndustryRankItem], summary="업종별 폐업률 순위 (F-MAP-05)")
def industries(q: Annotated[IndustryRankQuery, Query()], db: DB):
    # 필터와 정렬 기준·개수를 서비스에 넘긴다.
    return market_service.get_industries(db, q, q.sort_by, q.top_n)
