# [역할] 상권 서비스 — 저장소 결과에 신호등 색·표본 배지·역전 구간을 붙여 응답 스키마로 만든다.
"""상권 조회(F-MAP-01~05): repo 행 → 응답 스키마. 신호등 색·표본 배지·역전 구간을 여기서 붙인다."""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# DB 세션 타입.
from sqlalchemy.orm import Session

# 신호등 기준·표본 기준 설정.
from app.core import config
# 분기 표기 변환.
from app.domain import quarter as qt
# 표본 적음 판정, 신호등 색 계산.
from app.domain.market_signal import is_small_sample, signal_light
# 역전 구간 탐지.
from app.domain.trend import find_reversals
# 상권 SQL 쿼리 모음.
from app.repo import market_repo
# 필터 메타·목록 응답·공통 필터.
from app.schemas.common import FilterMeta, ListResponse, MarketFilter
# 상권 응답 스키마들.
from app.schemas.market import (
    # 셀 분기 한 점
    CellPoint,
    # 셀 응답
    CellResponse,
    # 행정동 항목
    DongItem,
    # 랭킹 항목
    IndustryRankItem,
    # 자치구 항목
    RegionItem,
    # 추이 한 점
    TrendPoint,
    # 추이 응답
    TrendResponse,
    # 역전 한 건
    TrendReversal,
)
# 404·422 예외.
from app.service.errors import InvalidInputError, NotFoundError

# 엔드포인트별로 데이터 단위상 적용 가능한 필터. 나머지는 meta.ignored_filters 로 알린다.
SUPPORTED_REGIONS = {"gu", "industry_group", "min_store_count"}
# /dongs: 자치구는 경로로 받으므로 필터 목록엔 없다.
SUPPORTED_DONGS = {"industry_group", "min_store_count"}
# /cells: 기간·업종·최소 점포수.
SUPPORTED_CELLS = {"start_quarter", "end_quarter", "industry_code", "min_store_count"}
# /trends: 기간·산업·최소 점포수.
SUPPORTED_TRENDS = {"start_quarter", "end_quarter", "industry_group", "min_store_count"}
# /industries: 산업·업종·최소 점포수.
SUPPORTED_INDUSTRIES = {"industry_group", "industry_code", "min_store_count"}


# 위험 순위 → 신호등 색(설정의 기준값 사용).
def _light(rank: float | None):
    # 도메인 함수에 기준값을 넘겨 계산한다.
    return signal_light(rank, green_max=config.SIGNAL_LIGHT_GREEN_MAX, yellow_max=config.SIGNAL_LIGHT_YELLOW_MAX)


# 점포 수 → '표본 적음' 여부(설정의 기준값 사용).
def _small(n: int | None) -> bool:
    # 도메인 함수에 기준값을 넘겨 판정한다.
    return is_small_sample(n, threshold=config.SMALL_SAMPLE_MAX_STORES)


# F-MAP-01: 자치구 지도 응답을 만든다.
def get_regions(db: Session, f: MarketFilter) -> ListResponse[RegionItem]:
    # 저장소에서 가져온 각 행을 RegionItem 으로 바꾼다.
    items = [
        # 항목 하나 만들기
        RegionItem(
            # 자치구
            gu_name=r["gu_name"],
            # 산업대분류
            kosis_industry1=r["kosis_industry1"],
            # 위험 순위로 신호등 색 결정
            signal_light=_light(r["risk_rank"]),
            # 위험가중치
            risk_weight=r["risk_weight"],
            # 위험 순위
            risk_rank=r["risk_rank"],
            # 실질폐업률
            real_closure_rate=r["real_closure_rate"],
            # 평균폐업률
            avg_closure_rate=r["avg_closure_rate"],
            # 점포 수
            store_count=r["store_count"],
            # 표본 적음 여부
            small_sample=_small(r["store_count"]),
        )
        # 저장소 결과를 하나씩 돌면서
        for r in market_repo.fetch_regions(db, f)
        # 위험가중치·순위가 없는 행은 색을 정할 수 없으니 뺀다.
        if r["risk_weight"] is not None and r["risk_rank"] is not None
    ]
    # 항목과 필터 메타를 묶어 돌려준다.
    return ListResponse[RegionItem](items=items, meta=FilterMeta.of(f, SUPPORTED_REGIONS))


# F-MAP-02: 자치구 안 행정동×산업 성적표를 만든다.
def get_dongs(db: Session, gu: str, f: MarketFilter) -> ListResponse[DongItem]:
    # 자치구의 행정동 목록을 가져온다.
    districts = market_repo.fetch_districts_in_gu(db, gu)
    # 하나도 없으면 없는 자치구다.
    if not districts:
        # 404 로 알린다.
        raise NotFoundError(f"자치구를 찾을 수 없습니다: {gu}")
    # 산업 필터가 있으면 그것을, 없으면 패널에 있는 모든 산업을 쓴다.
    groups = f.industry_group or market_repo.fetch_panel_industry_groups(db)
    # 행정동×산업 위험 가중치를 한 번에 가져온다.
    risk = market_repo.fetch_region_risk(db, [d["district_code"] for d in districts], groups)

    # 결과 항목 목록.
    items: list[DongItem] = []
    # 행정동마다
    for d in districts:
        # 산업마다
        for g in groups:
            # 해당 조합의 집계 행(없으면 None)
            r = risk.get((d["district_code"], g))
            # 집계가 있고 점포 수 합이 최소 기준 이상이면 정상
            ok = r is not None and (r["store_count_sum"] or 0) >= f.min_store_count
            # 항목을 추가한다.
            items.append(
                # 항목 하나 만들기
                DongItem(
                    # 행정동 코드
                    district_code=d["district_code"],
                    # 행정동 이름
                    district_name=d["district_name"],
                    # 산업대분류
                    kosis_industry1=g,
                    # 정상이면 ok, 아니면 표본부족
                    sample_status="ok" if ok else "insufficient",
                    # 정상일 때만 신호등 색(위험 순위 기준)
                    signal_light=_light(r["risk_rank"]) if ok else None,
                    # 정상일 때만 위험가중치
                    risk_weight=r["risk_weight"] if ok else None,
                    # 정상일 때만 위험 순위
                    risk_rank=r["risk_rank"] if ok else None,
                    # 정상일 때만 평균폐업률
                    avg_closure_rate=r["avg_closure_rate"] if ok else None,
                    # 정상일 때만 폐업개업격차
                    open_close_gap=r["open_close_gap"] if ok else None,
                    # 정상일 때만 관측 분기 수
                    quarter_count=r["quarter_count"] if ok else None,
                )
            )
    # 필터 메타를 만든다.
    meta = FilterMeta.of(f, SUPPORTED_DONGS)
    # 경로의 gu 가 필터의 gu 보다 우선이다. 다르면 무시됐다고 알린다.
    if f.gu and f.gu != gu and "gu" not in meta.ignored_filters:
        # 무시 목록에 gu 를 더한다.
        meta.ignored_filters.append("gu")
    # 항목과 메타를 묶어 돌려준다.
    return ListResponse[DongItem](items=items, meta=meta)


# F-MAP-03: 행정동×업종 상세 카드를 만든다.
def get_cells(db: Session, district_code: str, f: MarketFilter) -> CellResponse:
    # 업종 코드가 없으면
    if not f.industry_code:
        # 422 로 알린다.
        raise InvalidInputError("industry_code 는 필수입니다.")
    # 행정동 정보를 가져온다.
    district = market_repo.fetch_district(db, district_code)
    # 없는 행정동이면
    if district is None:
        # 404.
        raise NotFoundError(f"행정동을 찾을 수 없습니다: {district_code}")
    # 업종 정보를 가져온다.
    industry = market_repo.fetch_industry(db, f.industry_code)
    # 없는 업종이면
    if industry is None:
        # 404.
        raise NotFoundError(f"업종을 찾을 수 없습니다: {f.industry_code}")

    # 분기별 시계열 행들을 가져온다.
    rows = market_repo.fetch_cell_series(db, district_code, f.industry_code, f)
    # 각 행을 CellPoint 로 바꾼다.
    points = [
        # 점 하나 만들기
        CellPoint(
            # DB 분기 코드를 API 형식으로
            quarter=qt.db_to_api(r["quarter_code"]),
            # 점포 수
            store_count=r["store_count"],
            # 폐업률
            closure_rate=r["closure_rate"],
            # 개업률
            open_rate=r["open_rate"],
            # 폐업개업격차
            open_close_gap=r["open_close_gap"],
            # 업종 내 percentile
            closure_pctl_in_industry=r["closure_pctl_in_industry"],
            # 표본 적음 여부
            small_sample=_small(r["store_count"]),
        )
        # 행마다 반복
        for r in rows
    ]
    # 응답을 만들어 돌려준다.
    return CellResponse(
        # 행정동 코드
        district_code=district_code,
        # 행정동 이름
        district_name=district["district_name"],
        # 업종 코드
        industry_code=f.industry_code,
        # 업종 이름
        industry_name=industry["industry_name"],
        # 시계열
        points=points,
        # 필터 메타
        meta=FilterMeta.of(f, SUPPORTED_CELLS),
    )


# F-MAP-04: 분기 추이와 역전 구간 응답을 만든다.
def get_trends(db: Session, f: MarketFilter) -> TrendResponse:
    # 추이 행들을 가져온다.
    rows = market_repo.fetch_trends(db, f)
    # 각 행을 TrendPoint 로 바꾼다.
    items = [
        # 점 하나 만들기
        TrendPoint(
            # 분기(API 형식)
            quarter=qt.db_to_api(r["quarter_code"]),
            # 산업대분류
            kosis_industry1=r["kosis_industry1"],
            # 평균폐업률
            avg_closure_rate=r["avg_closure_rate"],
            # 평균개업률
            avg_open_rate=r["avg_open_rate"],
            # 실질폐업률
            real_closure_rate=r["real_closure_rate"],
            # 점포 수
            store_count=r["store_count"],
        )
        # 행마다 반복
        for r in rows
    ]
    # 역전 구간을 계산해 응답 모델로 바꾼다.
    reversals = [
        # 역전 한 건을 스키마로
        TrendReversal(kosis_industry1=x.group, quarter=x.quarter, direction=x.direction)
        # (산업, 분기, 개업률, 폐업률)을 넘겨 찾은 역전마다
        for x in find_reversals((p.kosis_industry1, p.quarter, p.avg_open_rate, p.avg_closure_rate) for p in items)
    ]
    # 추이·역전·메타를 묶어 돌려준다.
    return TrendResponse(items=items, reversals=reversals, meta=FilterMeta.of(f, SUPPORTED_TRENDS))


# F-MAP-05: 업종 랭킹 응답을 만든다.
def get_industries(db: Session, f: MarketFilter, sort_by: str, top_n: int) -> ListResponse[IndustryRankItem]:
    # 정렬·개수가 적용된 랭킹 행들을 가져온다.
    rows = market_repo.fetch_industry_rank(db, f, sort_by, top_n)
    # 순서대로 순위를 매겨 항목으로 바꾼다.
    items = [
        # 항목 하나 만들기
        IndustryRankItem(
            # 순위(1부터)
            rank=i,
            # 업종 코드
            industry_code=r["industry_code"],
            # 업종 이름
            industry_name=r["industry_name"],
            # 산업대분류
            kosis_industry1=r["kosis_industry1"],
            # 평균폐업률
            avg_closure_rate=r["avg_closure_rate"],
            # 실질폐업률
            real_closure_rate=r["real_closure_rate"],
            # 관측 수
            observation_count=r["observation_count"],
            # 점포 수
            store_count=r["store_count"],
        )
        # 1부터 번호를 매기며 반복
        for i, r in enumerate(rows, start=1)
    ]
    # 항목과 메타를 묶어 돌려준다.
    return ListResponse[IndustryRankItem](items=items, meta=FilterMeta.of(f, SUPPORTED_INDUSTRIES))
