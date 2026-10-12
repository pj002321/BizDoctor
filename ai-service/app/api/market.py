"""GET /api/market/* — 상권 '신호등'(F-MAP-01~05). 공통 필터는 F-MAP-06."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.common import ListResponse, MarketFilter
from app.schemas.market import (
    CellQuery,
    CellResponse,
    DongItem,
    IndustryRankItem,
    IndustryRankQuery,
    RegionItem,
    TrendResponse,
)
from app.service import market_service

router = APIRouter(prefix="/api/market", tags=["market"])

Filter = Annotated[MarketFilter, Query()]
DB = Annotated[Session, Depends(get_db)]


@router.get("/regions", response_model=ListResponse[RegionItem], summary="자치구 위험도 지도 (F-MAP-01)")
def regions(f: Filter, db: DB):
    return market_service.get_regions(db, f)


@router.get("/regions/{gu}/dongs", response_model=ListResponse[DongItem], summary="행정동 드릴다운 (F-MAP-02)")
def dongs(gu: Annotated[str, Path(description="자치구명", examples=["마포구"])], f: Filter, db: DB):
    return market_service.get_dongs(db, gu, f)


@router.get("/cells", response_model=CellResponse, summary="행정동×업종 상세 카드 (F-MAP-03)")
def cells(q: Annotated[CellQuery, Query()], db: DB):
    return market_service.get_cells(db, q.district_code, q)


@router.get("/trends", response_model=TrendResponse, summary="분기별 산업 추이 (F-MAP-04)")
def trends(f: Filter, db: DB):
    return market_service.get_trends(db, f)


@router.get("/industries", response_model=ListResponse[IndustryRankItem], summary="업종별 폐업률 순위 (F-MAP-05)")
def industries(q: Annotated[IndustryRankQuery, Query()], db: DB):
    return market_service.get_industries(db, q, q.sort_by, q.top_n)
