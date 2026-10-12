"""상권 조회(F-MAP-01~05) 응답. 여기서 '신호등'은 지역 단위 결과다(F-SYS-01)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core import config
from app.domain.market_signal import MarketSignalLight
from app.schemas.common import FilterMeta, MarketFilter


class RegionItem(BaseModel):
    gu_name: str
    kosis_industry1: str
    signal_light: MarketSignalLight
    risk_weight: float = Field(description="위험가중치(percentile 평균, 0~1)")
    risk_rank: float = Field(description="같은 산업대분류 자치구들 사이 위험가중치 순위(0~1). 신호등 색 기준")
    real_closure_rate: float | None = Field(description="실질폐업률(가중, %) — 기본 표기")
    avg_closure_rate: float | None = Field(description="평균폐업률(%) — 보조 표기")
    store_count: int
    small_sample: bool


class DongItem(BaseModel):
    district_code: str
    district_name: str
    kosis_industry1: str
    sample_status: Literal["ok", "insufficient"] = Field(
        description="insufficient = 관측 8분기·연점포수 100 미만이라 집계가 없는 조합('표본부족')"
    )
    signal_light: MarketSignalLight | None
    risk_weight: float | None
    risk_rank: float | None = Field(description="같은 산업대분류 행정동들 사이 위험가중치 순위(0~1). 신호등 색 기준")
    avg_closure_rate: float | None
    open_close_gap: float | None = Field(description="폐업개업격차(%p) — 양수면 위축 국면")
    quarter_count: int | None


class CellPoint(BaseModel):
    quarter: str
    store_count: int
    closure_rate: float | None
    open_rate: float | None
    open_close_gap: float | None
    closure_pctl_in_industry: float | None
    small_sample: bool = Field(description="점포 수 5 이하 — UI 에 '표본 적음' 배지 필수")


class CellResponse(BaseModel):
    district_code: str
    district_name: str
    industry_code: str
    industry_name: str
    points: list[CellPoint]
    meta: FilterMeta


class TrendPoint(BaseModel):
    quarter: str
    kosis_industry1: str
    avg_closure_rate: float | None
    avg_open_rate: float | None
    real_closure_rate: float | None
    store_count: int


class TrendReversal(BaseModel):
    kosis_industry1: str
    quarter: str
    direction: Literal["closure_over_open", "open_over_closure"]


class TrendResponse(BaseModel):
    items: list[TrendPoint]
    reversals: list[TrendReversal] = Field(description="개업률-폐업률 역전 분기(차트 주석용)")
    meta: FilterMeta


class IndustryRankItem(BaseModel):
    rank: int
    industry_code: str
    industry_name: str
    kosis_industry1: str | None
    avg_closure_rate: float | None
    real_closure_rate: float | None
    observation_count: int
    store_count: int


class CellQuery(MarketFilter):
    district_code: str = Field(pattern=r"^\d{8,10}$", description="행정동 코드")


class IndustryRankQuery(MarketFilter):
    sort_by: Literal["avg_closure_rate", "real_closure_rate"] = "avg_closure_rate"
    top_n: int = Field(config.INDUSTRY_RANK_TOP_N_MAX, ge=1, le=config.INDUSTRY_RANK_TOP_N_MAX)
