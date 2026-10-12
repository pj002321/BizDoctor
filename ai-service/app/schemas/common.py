"""F-MAP-06 공통 필터와 응답 메타."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core import config
from app.domain.quarter import API_QUARTER_PATTERN

T = TypeVar("T")


class MarketFilter(BaseModel):
    """지도·차트·표가 같은 필터 상태를 공유한다. 엔드포인트마다 적용 가능한 필드만 쓰고,
    적용 못 한 필드는 meta.ignored_filters 로 돌려준다(조용히 무시하지 않는다)."""

    model_config = ConfigDict(extra="forbid")

    start_quarter: str | None = Field(None, pattern=API_QUARTER_PATTERN, examples=["2023Q1"])
    end_quarter: str | None = Field(None, pattern=API_QUARTER_PATTERN, examples=["2025Q4"])
    gu: str | None = Field(None, description="자치구명", examples=["마포구"])
    industry_group: list[str] | None = Field(None, description="산업대분류(KOSIS_산업1), 복수 가능")
    industry_code: str | None = Field(None, description="서비스 업종 코드", examples=["CS100001"])
    min_store_count: int = Field(config.MIN_STORE_COUNT_DEFAULT, ge=1, description="최소 점포 수")

    @model_validator(mode="after")
    def _period_order(self) -> MarketFilter:
        if self.start_quarter and self.end_quarter and self.start_quarter > self.end_quarter:
            raise ValueError("start_quarter 가 end_quarter 보다 늦습니다.")
        return self

    def active_fields(self) -> set[str]:
        """사용자가 실제로 건 필터. min_store_count 는 기본값이 있어 항상 활성.
        하위 쿼리 모델이 더한 필드(district_code·sort_by 등)는 필터가 아니므로 뺀다."""
        return {k for k in MarketFilter.model_fields if getattr(self, k) not in (None, [])}


class FilterMeta(BaseModel):
    applied_filters: list[str]
    ignored_filters: list[str] = Field(description="이 엔드포인트의 데이터 단위로는 적용할 수 없어 무시된 필터")

    @classmethod
    def of(cls, f: MarketFilter, supported: set[str]) -> FilterMeta:
        active = f.active_fields()
        return cls(applied_filters=sorted(active & supported), ignored_filters=sorted(active - supported))


class ListResponse(BaseModel, Generic[T]):
    items: list[T]
    meta: FilterMeta
