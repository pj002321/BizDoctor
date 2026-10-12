"""상권 조회(F-MAP) 쿼리. 사전 집계 테이블만 읽는다(F-SYS-02) — fact_panel 은 셀 상세에서
(행정동, 업종) 한 쌍으로 좁혀서만 읽는다."""
from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.domain import quarter as qt
from app.model.tables import (
    dim_district,
    dim_industry,
    fact_panel,
    fact_region_risk,
    industry_rank,
    quarterly_trend,
    region_summary,
    v_featured,
)
from app.schemas.common import MarketFilter


def _quarter_range(col, f: MarketFilter) -> list:
    conds = []
    if f.start_quarter:
        conds.append(col >= qt.api_to_db(f.start_quarter))
    if f.end_quarter:
        conds.append(col <= qt.api_to_db(f.end_quarter))
    return conds


def fetch_regions(db: Session, f: MarketFilter) -> list[dict]:
    t = region_summary
    stmt = select(t).where(t.c.store_count >= f.min_store_count)
    if f.gu:
        stmt = stmt.where(t.c.gu_name == f.gu)
    if f.industry_group:
        stmt = stmt.where(t.c.kosis_industry1.in_(f.industry_group))
    stmt = stmt.order_by(t.c.gu_name, t.c.kosis_industry1)
    return [dict(r._mapping) for r in db.execute(stmt)]


def fetch_districts_in_gu(db: Session, gu: str) -> list[dict]:
    t = dim_district
    stmt = select(t.c.district_code, t.c.district_name).where(t.c.gu_name == gu).order_by(t.c.district_name)
    return [dict(r._mapping) for r in db.execute(stmt)]


def fetch_panel_industry_groups(db: Session) -> list[str]:
    """패널에 실제로 쓰이는 산업대분류(ERD: 8개). 미매핑(NULL)은 제외."""
    c = dim_industry.c.kosis_industry1
    return list(db.scalars(select(c).where(c.is_not(None)).distinct().order_by(c)))


def fetch_region_risk(db: Session, district_codes: list[str], groups: list[str]) -> dict[tuple[str, str], dict]:
    t = fact_region_risk
    stmt = select(t).where(t.c.district_code.in_(district_codes), t.c.kosis_industry1.in_(groups))
    return {(r.district_code, r.kosis_industry1): dict(r._mapping) for r in db.execute(stmt)}


def fetch_district(db: Session, district_code: str) -> dict | None:
    r = db.execute(select(dim_district).where(dim_district.c.district_code == district_code)).first()
    return dict(r._mapping) if r else None


def fetch_industry(db: Session, industry_code: str) -> dict | None:
    r = db.execute(select(dim_industry).where(dim_industry.c.industry_code == industry_code)).first()
    return dict(r._mapping) if r else None


def fetch_cell_series(db: Session, district_code: str, industry_code: str, f: MarketFilter) -> list[dict]:
    p, v = fact_panel, v_featured
    stmt = (
        select(
            p.c.quarter_code, p.c.store_count, p.c.closure_rate, p.c.open_rate,
            v.c.open_close_gap, v.c.closure_pctl_in_industry,
        )
        .select_from(
            p.outerjoin(
                v,
                and_(
                    v.c.district_code == p.c.district_code,
                    v.c.industry_code == p.c.industry_code,
                    v.c.quarter_code == p.c.quarter_code,
                ),
            )
        )
        .where(
            p.c.district_code == district_code,
            p.c.industry_code == industry_code,
            p.c.store_count >= f.min_store_count,
            *_quarter_range(p.c.quarter_code, f),
        )
        .order_by(p.c.quarter_code)
    )
    return [dict(r._mapping) for r in db.execute(stmt)]


def fetch_trends(db: Session, f: MarketFilter) -> list[dict]:
    t = quarterly_trend
    stmt = select(t).where(t.c.store_count >= f.min_store_count, *_quarter_range(t.c.quarter_code, f))
    if f.industry_group:
        stmt = stmt.where(t.c.kosis_industry1.in_(f.industry_group))
    stmt = stmt.order_by(t.c.kosis_industry1, t.c.quarter_code)
    return [dict(r._mapping) for r in db.execute(stmt)]


def fetch_industry_rank(db: Session, f: MarketFilter, sort_by: str, top_n: int) -> list[dict]:
    t = industry_rank
    sort_col = {"avg_closure_rate": t.c.avg_closure_rate, "real_closure_rate": t.c.real_closure_rate}[sort_by]
    stmt = select(t).where(t.c.store_count >= f.min_store_count)
    if f.industry_group:
        stmt = stmt.where(t.c.kosis_industry1.in_(f.industry_group))
    if f.industry_code:
        stmt = stmt.where(t.c.industry_code == f.industry_code)
    stmt = stmt.order_by(sort_col.desc().nulls_last(), t.c.industry_code).limit(top_n)
    return [dict(r._mapping) for r in db.execute(stmt)]
