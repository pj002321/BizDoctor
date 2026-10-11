# [역할] 상권 스키마 — 자치구·행정동·셀·추이·랭킹 응답 모델과 /cells·/industries 전용 쿼리 모델.
"""상권 조회(F-MAP-01~05) 응답. 여기서 '신호등'은 지역 단위 결과다(F-SYS-01)."""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 정해진 값만 허용하는 타입.
from typing import Literal

# 스키마 기반 클래스·필드 옵션.
from pydantic import BaseModel, Field

# 랭킹 최대 개수 설정.
from app.core import config
# 상권 신호등 색 타입.
from app.domain.market_signal import MarketSignalLight
# 필터 메타와 공통 필터(상속용).
from app.schemas.common import FilterMeta, MarketFilter


# /regions 항목 — 자치구×산업 하나.
class RegionItem(BaseModel):  # F-MAP-01
    # 자치구 이름
    gu_name: str
    # 산업대분류
    kosis_industry1: str
    # 신호등 색
    signal_light: MarketSignalLight
    # 위험가중치
    risk_weight: float = Field(description="위험가중치(percentile 평균, 0~1)")
    # 색을 정하는 값
    risk_rank: float = Field(description="같은 산업대분류 자치구들 사이 위험가중치 순위(0~1). 신호등 색 기준")
    # 실질폐업률 — 화면 기본 표기
    real_closure_rate: float | None = Field(description="실질폐업률(가중, %) — 기본 표기")
    # 평균폐업률 — 보조 표기
    avg_closure_rate: float | None = Field(description="평균폐업률(%) — 보조 표기")
    # 점포 수
    store_count: int
    # '표본 적음' 배지 여부
    small_sample: bool


# /dongs 항목 — 행정동×산업 하나.
class DongItem(BaseModel):  # F-MAP-02
    # 행정동 코드
    district_code: str
    # 행정동 이름
    district_name: str
    # 산업대분류
    kosis_industry1: str
    # 집계가 있는지('ok') 없는지('insufficient' = 표본부족)
    sample_status: Literal["ok", "insufficient"] = Field(
        # 문서 설명
        description="insufficient = 관측 8분기·연점포수 100 미만이라 집계가 없는 조합('표본부족')"
    )
    # 신호등 색(표본부족이면 null)
    signal_light: MarketSignalLight | None
    # 위험가중치
    risk_weight: float | None
    # 색을 정하는 값
    risk_rank: float | None = Field(description="같은 산업대분류 행정동들 사이 위험가중치 순위(0~1). 신호등 색 기준")
    # 평균폐업률
    avg_closure_rate: float | None
    # 폐업률 - 개업률
    open_close_gap: float | None = Field(description="폐업개업격차(%p) — 양수면 위축 국면")
    # 관측된 분기 수
    quarter_count: int | None


# /cells 의 분기 한 점.
class CellPoint(BaseModel):  # F-MAP-03 분기 한 점
    # 분기(예: 2025Q4)
    quarter: str
    # 점포 수
    store_count: int
    # 폐업률
    closure_rate: float | None
    # 개업률
    open_rate: float | None
    # 폐업개업격차
    open_close_gap: float | None
    # 업종 내 percentile
    closure_pctl_in_industry: float | None
    # '표본 적음' 배지 여부
    small_sample: bool = Field(description="점포 수 5 이하 — UI 에 '표본 적음' 배지 필수")


# /cells 응답 전체.
class CellResponse(BaseModel):
    # 행정동 코드
    district_code: str
    # 행정동 이름
    district_name: str
    # 업종 코드
    industry_code: str
    # 업종 이름
    industry_name: str
    # 분기별 시계열
    points: list[CellPoint]
    # 필터 적용 결과
    meta: FilterMeta


# /trends 의 분기×산업 한 점.
class TrendPoint(BaseModel):  # F-MAP-04
    # 분기
    quarter: str
    # 산업대분류
    kosis_industry1: str
    # 평균폐업률
    avg_closure_rate: float | None
    # 평균개업률
    avg_open_rate: float | None
    # 실질폐업률
    real_closure_rate: float | None
    # 점포 수
    store_count: int


# 개업률·폐업률 역전 한 건.
class TrendReversal(BaseModel):
    # 산업대분류
    kosis_industry1: str
    # 역전 분기
    quarter: str
    # 방향: 폐업률이 앞지름 / 개업률이 앞지름
    direction: Literal["closure_over_open", "open_over_closure"]


# /trends 응답 전체.
class TrendResponse(BaseModel):
    # 시계열 점들
    items: list[TrendPoint]
    # 차트 주석용 역전 분기들
    reversals: list[TrendReversal] = Field(description="개업률-폐업률 역전 분기(차트 주석용)")
    # 필터 적용 결과
    meta: FilterMeta


# /industries 항목 — 업종 하나.
class IndustryRankItem(BaseModel):  # F-MAP-05
    # 순위(1부터)
    rank: int
    # 업종 코드
    industry_code: str
    # 업종 이름
    industry_name: str
    # 산업대분류
    kosis_industry1: str | None
    # 평균폐업률
    avg_closure_rate: float | None
    # 실질폐업률
    real_closure_rate: float | None
    # 관측 수(200 이상만 들어 있다)
    observation_count: int
    # 점포 수
    store_count: int


# --- 엔드포인트 전용 쿼리 ---------------------------------------------------
# FastAPI 의 쿼리 모델은 다른 쿼리 파라미터와 섞어 쓸 수 없다. 그래서 공통 필터를 상속해 넓힌다.
class CellQuery(MarketFilter):
    # 공통 필터에 행정동 코드(필수)를 더한다.
    district_code: str = Field(pattern=r"^\d{8,10}$", description="행정동 코드")


# /industries 쿼리 — 공통 필터 + 정렬 기준·개수.
class IndustryRankQuery(MarketFilter):
    # 정렬 기준(평균폐업률 또는 실질폐업률), 기본은 평균폐업률.
    sort_by: Literal["avg_closure_rate", "real_closure_rate"] = "avg_closure_rate"
    # 돌려줄 개수: 1~100, 기본 100.
    top_n: int = Field(config.INDUSTRY_RANK_TOP_N_MAX, ge=1, le=config.INDUSTRY_RANK_TOP_N_MAX)
