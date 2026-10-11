# [역할] 피처 저장소 — 최신 분기, 행정동×업종 정적 피처, 업종 중앙값(폴백), 업종 폐업률 분포를 조회한다 (F-DIA-02·07).
"""F-DIA-02 정적 피처 · F-DIA-07 분포 조회."""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# and_: 조건 묶기, func: SQL 함수(max·percentile_cont), select: SELECT 문.
from sqlalchemy import and_, func, select
# DB 세션 타입.
from sqlalchemy.orm import Session

# 분기별 원자료(fact_panel)와 파생 피처 뷰(v_featured).
from app.model.tables import fact_panel, v_featured


# 피처 뷰에 들어 있는 가장 최근 분기 코드를 돌려준다.
def latest_quarter(db: Session) -> str | None:
    # SELECT max(quarter_code) FROM v_featured 결과 한 값을 돌려준다.
    return db.scalar(select(func.max(v_featured.c.quarter_code)))


# fact_panel 과 v_featured 를 (행정동, 업종, 분기)로 이어 붙인 조인 객체를 만든다.
def _joined():
    # 짧은 이름으로 쓴다.
    p, v = fact_panel, v_featured
    # p 에 v 를 INNER JOIN 한다.
    return p.join(
        # 붙일 테이블
        v,
        # 세 키가 모두 같아야 한다.
        and_(
            # 행정동 코드 일치
            v.c.district_code == p.c.district_code,
            # 업종 코드 일치
            v.c.industry_code == p.c.industry_code,
            # 분기 일치
            v.c.quarter_code == p.c.quarter_code,
        ),
    )


# 특정 행정동×업종×분기의 정적 피처를 딕셔너리로 돌려준다(없으면 None).
def cell_features(db: Session, district_code: str, industry_code: str, quarter_code: str) -> dict | None:
    # 짧은 이름으로 쓴다.
    p, v = fact_panel, v_featured
    # 쿼리를 조립한다.
    stmt = (
        # 모델에 필요한 피처 4개와 점포 수를 고른다.
        select(v.c.closure_pctl_in_industry, p.c.closure_rate, p.c.open_rate, v.c.franchise_ratio, p.c.store_count)
        # 두 테이블을 조인한 결과에서
        .select_from(_joined())
        # 해당 행정동·업종·분기만 남긴다.
        .where(p.c.district_code == district_code, p.c.industry_code == industry_code, p.c.quarter_code == quarter_code)
    )
    # 실행해 첫 행을 가져온다.
    r = db.execute(stmt).first()
    # 있으면 딕셔너리로, 없으면 None.
    return dict(r._mapping) if r else None


# 같은 업종·분기 서울 전체의 피처 중앙값을 돌려준다.
def industry_medians(db: Session, industry_code: str, quarter_code: str) -> dict:
    """같은 업종·분기 서울 전체 중앙값 — 셀이 없거나 값이 비었을 때의 폴백."""
    # 짧은 이름으로 쓴다.
    p, v = fact_panel, v_featured

    # 컬럼을 받아 Postgres 중앙값 식(percentile_cont(0.5) WITHIN GROUP (ORDER BY col))을 만든다.
    def med(col):
        # 50% 지점 값을 구하는 SQL 식을 돌려준다.
        return func.percentile_cont(0.5).within_group(col)

    # 쿼리를 조립한다.
    stmt = (
        # 네 피처의 중앙값을 각각 같은 이름으로 고른다.
        select(
            # 업종 내 폐업률 percentile 중앙값
            med(v.c.closure_pctl_in_industry).label("closure_pctl_in_industry"),
            # 폐업률 중앙값
            med(p.c.closure_rate).label("closure_rate"),
            # 개업률 중앙값
            med(p.c.open_rate).label("open_rate"),
            # 프랜차이즈 비중 중앙값
            med(v.c.franchise_ratio).label("franchise_ratio"),
        )
        # 조인 결과에서
        .select_from(_joined())
        # 해당 업종·분기 행만 대상으로 한다.
        .where(p.c.industry_code == industry_code, p.c.quarter_code == quarter_code)
    )
    # 집계 결과 한 행을 딕셔너리로 돌려준다(데이터가 없으면 값이 전부 None).
    return dict(db.execute(stmt).one()._mapping)


# 같은 업종·분기 행정동들의 폐업률 값 목록을 돌려준다(분포 그림용).
def industry_closure_rates(db: Session, industry_code: str, quarter_code: str, min_store_count: int) -> list[float]:
    # 짧은 이름으로 쓴다.
    p = fact_panel
    # 폐업률만 고르되 조건을 건다.
    stmt = select(p.c.closure_rate).where(
        # 같은 업종
        p.c.industry_code == industry_code,
        # 같은 분기
        p.c.quarter_code == quarter_code,
        # 점포 수가 기준 이상인 셀만(이상치 제외)
        p.c.store_count >= min_store_count,
        # 폐업률이 비어 있지 않은 행만
        p.c.closure_rate.is_not(None),
    )
    # 첫 컬럼 값들만 꺼내 목록으로 돌려준다.
    return list(db.scalars(stmt))
