# [역할] 상권 저장소 — 지도·드릴다운·상세·추이·랭킹용 SQL 쿼리를 실행하고 필터 조건을 적용한다 (F-MAP).
"""상권 조회(F-MAP) 쿼리. 사전 집계 테이블만 읽는다(F-SYS-02) — fact_panel 은 셀 상세에서
(행정동, 업종) 한 쌍으로 좁혀서만 읽는다."""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# and_: 조건 묶기, select: SELECT 문 만들기.
from sqlalchemy import and_, select
# DB 세션 타입.
from sqlalchemy.orm import Session

# 분기 표기 변환(API ↔ DB).
from app.domain import quarter as qt
# 조회할 테이블들.
from app.model.tables import (
    # 행정동 기준표
    dim_district,
    # 업종 기준표
    dim_industry,
    # 분기별 원자료
    fact_panel,
    # 행정동×산업 위험 가중치
    fact_region_risk,
    # 업종 랭킹
    industry_rank,
    # 분기 추이
    quarterly_trend,
    # 자치구 요약
    region_summary,
    # 파생 피처 뷰
    v_featured,
)
# 공통 필터 타입.
from app.schemas.common import MarketFilter


# 필터의 기간(start/end)을 지정한 분기 컬럼에 걸 조건 목록으로 만든다.
def _quarter_range(col, f: MarketFilter) -> list:
    # 조건을 모을 목록
    conds = []
    # 시작 분기가 있으면
    if f.start_quarter:
        # '컬럼 >= 시작 분기(DB 형식)' 조건을 더한다.
        conds.append(col >= qt.api_to_db(f.start_quarter))
    # 끝 분기가 있으면
    if f.end_quarter:
        # '컬럼 <= 끝 분기' 조건을 더한다.
        conds.append(col <= qt.api_to_db(f.end_quarter))
    # 조건 목록을 돌려준다(없으면 빈 목록 → 조건 없음).
    return conds


# F-MAP-01: 자치구×산업 요약 행들을 가져온다.
def fetch_regions(db: Session, f: MarketFilter) -> list[dict]:
    # 짧은 이름으로 쓴다.
    t = region_summary
    # 최소 점포수 이상인 행만 고르는 기본 쿼리.
    stmt = select(t).where(t.c.store_count >= f.min_store_count)
    # 자치구 필터가 있으면
    if f.gu:
        # 그 자치구만 남긴다.
        stmt = stmt.where(t.c.gu_name == f.gu)
    # 산업대분류 필터가 있으면
    if f.industry_group:
        # 목록에 든 산업만 남긴다(IN).
        stmt = stmt.where(t.c.kosis_industry1.in_(f.industry_group))
    # 자치구·산업 순으로 정렬한다.
    stmt = stmt.order_by(t.c.gu_name, t.c.kosis_industry1)
    # 실행해서 각 행을 딕셔너리로 바꿔 돌려준다.
    return [dict(r._mapping) for r in db.execute(stmt)]


# 자치구 이름으로 그 안의 행정동 목록(코드·이름)을 가져온다.
def fetch_districts_in_gu(db: Session, gu: str) -> list[dict]:
    # 짧은 이름으로 쓴다.
    t = dim_district
    # 해당 자치구의 행정동 코드·이름을 이름순으로 고른다.
    stmt = select(t.c.district_code, t.c.district_name).where(t.c.gu_name == gu).order_by(t.c.district_name)
    # 딕셔너리 목록으로 돌려준다.
    return [dict(r._mapping) for r in db.execute(stmt)]


# 패널에서 실제로 쓰이는 산업대분류 목록을 가져온다.
def fetch_panel_industry_groups(db: Session) -> list[str]:
    """패널에 실제로 쓰이는 산업대분류(ERD: 8개). 미매핑(NULL)은 제외."""
    # 업종 기준표의 산업대분류 컬럼.
    c = dim_industry.c.kosis_industry1
    # NULL 을 뺀 중복 없는 값을 이름순으로 가져와 목록으로 돌려준다.
    return list(db.scalars(select(c).where(c.is_not(None)).distinct().order_by(c)))


# 여러 행정동×여러 산업의 위험 가중치를 (행정동코드, 산업) 키 딕셔너리로 가져온다.
def fetch_region_risk(db: Session, district_codes: list[str], groups: list[str]) -> dict[tuple[str, str], dict]:
    # 짧은 이름으로 쓴다.
    t = fact_region_risk
    # 주어진 행정동들과 산업들에 해당하는 행만 고른다.
    stmt = select(t).where(t.c.district_code.in_(district_codes), t.c.kosis_industry1.in_(groups))
    # (행정동코드, 산업) → 행 딕셔너리 형태로 돌려준다(없는 조합은 키가 없다 = 표본부족).
    return {(r.district_code, r.kosis_industry1): dict(r._mapping) for r in db.execute(stmt)}


# 행정동 코드로 기준표 한 행을 가져온다(없으면 None).
def fetch_district(db: Session, district_code: str) -> dict | None:
    # 코드가 일치하는 첫 행을 가져온다.
    r = db.execute(select(dim_district).where(dim_district.c.district_code == district_code)).first()
    # 있으면 딕셔너리, 없으면 None.
    return dict(r._mapping) if r else None


# 업종 코드로 기준표 한 행을 가져온다(없으면 None).
def fetch_industry(db: Session, industry_code: str) -> dict | None:
    # 코드가 일치하는 첫 행을 가져온다.
    r = db.execute(select(dim_industry).where(dim_industry.c.industry_code == industry_code)).first()
    # 있으면 딕셔너리, 없으면 None.
    return dict(r._mapping) if r else None


# F-MAP-03: 한 행정동×업종의 분기별 시계열을 가져온다.
def fetch_cell_series(db: Session, district_code: str, industry_code: str, f: MarketFilter) -> list[dict]:
    # 짧은 이름으로 쓴다.
    p, v = fact_panel, v_featured
    # 쿼리를 조립한다.
    stmt = (
        # 필요한 컬럼들을 고른다.
        select(
            # 분기·점포 수·폐업률·개업률(원자료)
            p.c.quarter_code, p.c.store_count, p.c.closure_rate, p.c.open_rate,
            # 폐업개업격차·업종 내 percentile(파생 피처)
            v.c.open_close_gap, v.c.closure_pctl_in_industry,
        )
        # 원자료에 피처 뷰를 LEFT JOIN 한다(피처가 없어도 원자료 행은 남긴다).
        .select_from(
            # LEFT OUTER JOIN
            p.outerjoin(
                # 붙일 뷰
                v,
                # 세 키가 모두 같을 때 붙인다.
                and_(
                    # 행정동 일치
                    v.c.district_code == p.c.district_code,
                    # 업종 일치
                    v.c.industry_code == p.c.industry_code,
                    # 분기 일치
                    v.c.quarter_code == p.c.quarter_code,
                ),
            )
        )
        # 조건을 건다.
        .where(
            # 해당 행정동
            p.c.district_code == district_code,
            # 해당 업종
            p.c.industry_code == industry_code,
            # 최소 점포수 이상
            p.c.store_count >= f.min_store_count,
            # 기간 조건(있으면)
            *_quarter_range(p.c.quarter_code, f),
        )
        # 분기 순으로 정렬한다.
        .order_by(p.c.quarter_code)
    )
    # 딕셔너리 목록으로 돌려준다.
    return [dict(r._mapping) for r in db.execute(stmt)]


# F-MAP-04: 분기×산업 추이 행들을 가져온다.
def fetch_trends(db: Session, f: MarketFilter) -> list[dict]:
    # 짧은 이름으로 쓴다.
    t = quarterly_trend
    # 최소 점포수와 기간 조건을 건 기본 쿼리.
    stmt = select(t).where(t.c.store_count >= f.min_store_count, *_quarter_range(t.c.quarter_code, f))
    # 산업대분류 필터가 있으면
    if f.industry_group:
        # 목록에 든 산업만 남긴다.
        stmt = stmt.where(t.c.kosis_industry1.in_(f.industry_group))
    # 산업·분기 순으로 정렬한다.
    stmt = stmt.order_by(t.c.kosis_industry1, t.c.quarter_code)
    # 딕셔너리 목록으로 돌려준다.
    return [dict(r._mapping) for r in db.execute(stmt)]


# F-MAP-05: 업종 랭킹을 정렬 기준·개수에 맞춰 가져온다.
def fetch_industry_rank(db: Session, f: MarketFilter, sort_by: str, top_n: int) -> list[dict]:
    # 짧은 이름으로 쓴다.
    t = industry_rank
    # 정렬 기준 문자열을 실제 컬럼으로 바꾼다(허용된 두 값만 존재 → SQL 주입 불가).
    sort_col = {"avg_closure_rate": t.c.avg_closure_rate, "real_closure_rate": t.c.real_closure_rate}[sort_by]
    # 최소 점포수 조건을 건 기본 쿼리.
    stmt = select(t).where(t.c.store_count >= f.min_store_count)
    # 산업대분류 필터가 있으면
    if f.industry_group:
        # 목록에 든 산업만 남긴다.
        stmt = stmt.where(t.c.kosis_industry1.in_(f.industry_group))
    # 업종 코드 필터가 있으면
    if f.industry_code:
        # 그 업종만 남긴다.
        stmt = stmt.where(t.c.industry_code == f.industry_code)
    # 기준 컬럼 내림차순(NULL 은 맨 뒤), 동률이면 업종 코드순으로 정렬하고 top_n 개만 자른다.
    stmt = stmt.order_by(sort_col.desc().nulls_last(), t.c.industry_code).limit(top_n)
    # 딕셔너리 목록으로 돌려준다.
    return [dict(r._mapping) for r in db.execute(stmt)]
