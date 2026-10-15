"""F-DIA-02 정적 피처 · F-DIA-07 분포 조회."""
from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.model.tables import fact_panel, v_featured


def latest_quarter(db: Session) -> str | None:
    return db.scalar(select(func.max(v_featured.c.quarter_code)))


def _joined():
    p, v = fact_panel, v_featured
    return p.join(
        v,
        and_(
            v.c.district_code == p.c.district_code,
            v.c.industry_code == p.c.industry_code,
            v.c.quarter_code == p.c.quarter_code,
        ),
    )


def cell_features(db: Session, district_code: str, industry_code: str, quarter_code: str) -> dict | None:
    p, v = fact_panel, v_featured
    stmt = (
        select(v.c.closure_pctl_in_industry, p.c.closure_rate, p.c.open_rate, v.c.franchise_ratio, p.c.store_count)
        .select_from(_joined())
        .where(p.c.district_code == district_code, p.c.industry_code == industry_code, p.c.quarter_code == quarter_code)
    )
    r = db.execute(stmt).first()
    return dict(r._mapping) if r else None


def industry_medians(db: Session, industry_code: str, quarter_code: str) -> dict:
    """같은 업종·분기 서울 전체 중앙값 — 셀이 없거나 값이 비었을 때의 폴백."""
    p, v = fact_panel, v_featured

    def med(col):
        return func.percentile_cont(0.5).within_group(col)

    stmt = (
        select(
            med(v.c.closure_pctl_in_industry).label("closure_pctl_in_industry"),
            med(p.c.closure_rate).label("closure_rate"),
            med(p.c.open_rate).label("open_rate"),
            med(v.c.franchise_ratio).label("franchise_ratio"),
        )
        .select_from(_joined())
        .where(p.c.industry_code == industry_code, p.c.quarter_code == quarter_code)
    )
    return dict(db.execute(stmt).one()._mapping)


def industry_closure_rates(db: Session, industry_code: str, quarter_code: str, min_store_count: int) -> list[float]:
    p = fact_panel
    stmt = select(p.c.closure_rate).where(
        p.c.industry_code == industry_code,
        p.c.quarter_code == quarter_code,
        p.c.store_count >= min_store_count,
        p.c.closure_rate.is_not(None),
    )
    return list(db.scalars(stmt))
