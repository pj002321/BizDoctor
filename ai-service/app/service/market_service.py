"""상권 조회(F-MAP-01~05): repo 행 → 응답 스키마. 신호등 색·표본 배지·역전 구간을 여기서 붙인다."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core import config
from app.domain import quarter as qt
from app.domain.market_signal import is_small_sample, signal_light
from app.domain.trend import find_reversals
from app.repo import market_repo
from app.schemas.common import FilterMeta, ListResponse, MarketFilter
from app.schemas.market import (
    CellPoint,
    CellResponse,
    DongItem,
    IndustryRankItem,
    RegionItem,
    TrendPoint,
    TrendResponse,
    TrendReversal,
)
from app.service.errors import InvalidInputError, NotFoundError

SUPPORTED_REGIONS = {"gu", "industry_group", "min_store_count"}
SUPPORTED_DONGS = {"industry_group", "min_store_count"}
SUPPORTED_CELLS = {"start_quarter", "end_quarter", "industry_code", "min_store_count"}
SUPPORTED_TRENDS = {"start_quarter", "end_quarter", "industry_group", "min_store_count"}
SUPPORTED_INDUSTRIES = {"industry_group", "industry_code", "min_store_count"}


def _light(rank: float | None):
    return signal_light(rank, green_max=config.SIGNAL_LIGHT_GREEN_MAX, yellow_max=config.SIGNAL_LIGHT_YELLOW_MAX)


def _small(n: int | None) -> bool:
    return is_small_sample(n, threshold=config.SMALL_SAMPLE_MAX_STORES)


def get_regions(db: Session, f: MarketFilter) -> ListResponse[RegionItem]:
    items = [
        RegionItem(
            gu_name=r["gu_name"],
            kosis_industry1=r["kosis_industry1"],
            signal_light=_light(r["risk_rank"]),
            risk_weight=r["risk_weight"],
            risk_rank=r["risk_rank"],
            real_closure_rate=r["real_closure_rate"],
            avg_closure_rate=r["avg_closure_rate"],
            store_count=r["store_count"],
            small_sample=_small(r["store_count"]),
        )
        for r in market_repo.fetch_regions(db, f)
        if r["risk_weight"] is not None and r["risk_rank"] is not None
    ]
    return ListResponse[RegionItem](items=items, meta=FilterMeta.of(f, SUPPORTED_REGIONS))


def get_dongs(db: Session, gu: str, f: MarketFilter) -> ListResponse[DongItem]:
    districts = market_repo.fetch_districts_in_gu(db, gu)
    if not districts:
        raise NotFoundError(f"자치구를 찾을 수 없습니다: {gu}")
    groups = f.industry_group or market_repo.fetch_panel_industry_groups(db)
    risk = market_repo.fetch_region_risk(db, [d["district_code"] for d in districts], groups)

    items: list[DongItem] = []
    for d in districts:
        for g in groups:
            r = risk.get((d["district_code"], g))
            ok = r is not None and (r["store_count_sum"] or 0) >= f.min_store_count
            items.append(
                DongItem(
                    district_code=d["district_code"],
                    district_name=d["district_name"],
                    kosis_industry1=g,
                    sample_status="ok" if ok else "insufficient",
                    signal_light=_light(r["risk_rank"]) if ok else None,
                    risk_weight=r["risk_weight"] if ok else None,
                    risk_rank=r["risk_rank"] if ok else None,
                    avg_closure_rate=r["avg_closure_rate"] if ok else None,
                    open_close_gap=r["open_close_gap"] if ok else None,
                    quarter_count=r["quarter_count"] if ok else None,
                )
            )
    meta = FilterMeta.of(f, SUPPORTED_DONGS)
    if f.gu and f.gu != gu and "gu" not in meta.ignored_filters:
        meta.ignored_filters.append("gu")
    return ListResponse[DongItem](items=items, meta=meta)


def get_cells(db: Session, district_code: str, f: MarketFilter) -> CellResponse:
    if not f.industry_code:
        raise InvalidInputError("industry_code 는 필수입니다.")
    district = market_repo.fetch_district(db, district_code)
    if district is None:
        raise NotFoundError(f"행정동을 찾을 수 없습니다: {district_code}")
    industry = market_repo.fetch_industry(db, f.industry_code)
    if industry is None:
        raise NotFoundError(f"업종을 찾을 수 없습니다: {f.industry_code}")

    rows = market_repo.fetch_cell_series(db, district_code, f.industry_code, f)
    points = [
        CellPoint(
            quarter=qt.db_to_api(r["quarter_code"]),
            store_count=r["store_count"],
            closure_rate=r["closure_rate"],
            open_rate=r["open_rate"],
            open_close_gap=r["open_close_gap"],
            closure_pctl_in_industry=r["closure_pctl_in_industry"],
            small_sample=_small(r["store_count"]),
        )
        for r in rows
    ]
    return CellResponse(
        district_code=district_code,
        district_name=district["district_name"],
        industry_code=f.industry_code,
        industry_name=industry["industry_name"],
        points=points,
        meta=FilterMeta.of(f, SUPPORTED_CELLS),
    )


def get_trends(db: Session, f: MarketFilter) -> TrendResponse:
    rows = market_repo.fetch_trends(db, f)
    items = [
        TrendPoint(
            quarter=qt.db_to_api(r["quarter_code"]),
            kosis_industry1=r["kosis_industry1"],
            avg_closure_rate=r["avg_closure_rate"],
            avg_open_rate=r["avg_open_rate"],
            real_closure_rate=r["real_closure_rate"],
            store_count=r["store_count"],
        )
        for r in rows
    ]
    reversals = [
        TrendReversal(kosis_industry1=x.group, quarter=x.quarter, direction=x.direction)
        for x in find_reversals((p.kosis_industry1, p.quarter, p.avg_open_rate, p.avg_closure_rate) for p in items)
    ]
    return TrendResponse(items=items, reversals=reversals, meta=FilterMeta.of(f, SUPPORTED_TRENDS))


def get_industries(db: Session, f: MarketFilter, sort_by: str, top_n: int) -> ListResponse[IndustryRankItem]:
    rows = market_repo.fetch_industry_rank(db, f, sort_by, top_n)
    items = [
        IndustryRankItem(
            rank=i,
            industry_code=r["industry_code"],
            industry_name=r["industry_name"],
            kosis_industry1=r["kosis_industry1"],
            avg_closure_rate=r["avg_closure_rate"],
            real_closure_rate=r["real_closure_rate"],
            observation_count=r["observation_count"],
            store_count=r["store_count"],
        )
        for i, r in enumerate(rows, start=1)
    ]
    return ListResponse[IndustryRankItem](items=items, meta=FilterMeta.of(f, SUPPORTED_INDUSTRIES))
