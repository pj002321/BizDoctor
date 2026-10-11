# [역할] 공통 스키마 — 기간·자치구·산업·업종·최소 점포수 공통 필터와 적용/무시된 필터 메타, 목록 응답 틀 (F-MAP-06).
"""F-MAP-06 공통 필터와 응답 메타."""
# 타입 힌트를 늦게 평가한다(클래스 안에서 자기 자신을 타입으로 쓰기 위해).
from __future__ import annotations

# Generic·TypeVar: '어떤 항목 타입이든 담는 목록 응답'을 만들기 위한 도구.
from typing import Generic, TypeVar

# BaseModel: 스키마 기반 클래스, ConfigDict: 설정, Field: 필드 옵션, model_validator: 모델 단위 검증.
from pydantic import BaseModel, ConfigDict, Field, model_validator

# 최소 점포수 기본값을 읽을 설정.
from app.core import config
# 분기 형식 정규식 — 도메인과 같은 규칙을 쓴다.
from app.domain.quarter import API_QUARTER_PATTERN

# 목록 응답의 항목 타입 자리표시자.
T = TypeVar("T")


# 지도·차트·표가 함께 쓰는 공통 필터.
class MarketFilter(BaseModel):
    """지도·차트·표가 같은 필터 상태를 공유한다. 엔드포인트마다 적용 가능한 필드만 쓰고,
    적용 못 한 필드는 meta.ignored_filters 로 돌려준다(조용히 무시하지 않는다)."""

    # 정의되지 않은 필드는 받지 않는다.
    model_config = ConfigDict(extra="forbid")

    # 시작 분기(예: 2023Q1). 형식이 틀리면 422.
    start_quarter: str | None = Field(None, pattern=API_QUARTER_PATTERN, examples=["2023Q1"])
    # 끝 분기(예: 2025Q4).
    end_quarter: str | None = Field(None, pattern=API_QUARTER_PATTERN, examples=["2025Q4"])
    # 자치구명.
    gu: str | None = Field(None, description="자치구명", examples=["마포구"])
    # 산업대분류 — ?industry_group=A&industry_group=B 처럼 여러 개 가능.
    industry_group: list[str] | None = Field(None, description="산업대분류(KOSIS_산업1), 복수 가능")
    # 서비스 업종 코드.
    industry_code: str | None = Field(None, description="서비스 업종 코드", examples=["CS100001"])
    # 최소 점포 수. 기본 5, 1 미만이면 422.
    min_store_count: int = Field(config.MIN_STORE_COUNT_DEFAULT, ge=1, description="최소 점포 수")

    # 필드 검증이 모두 끝난 뒤 실행되는 모델 단위 검증.
    @model_validator(mode="after")
    def _period_order(self) -> MarketFilter:
        # 시작·끝이 다 있는데 시작이 더 늦으면('2025Q1' > '2024Q4' 는 문자열 비교로도 성립)
        if self.start_quarter and self.end_quarter and self.start_quarter > self.end_quarter:
            # 오류로 알린다(→ 422).
            raise ValueError("start_quarter 가 end_quarter 보다 늦습니다.")
        # 문제없으면 자기 자신을 돌려준다.
        return self

    # 사용자가 실제로 값을 넣은 필터 이름 집합을 돌려준다.
    def active_fields(self) -> set[str]:
        """사용자가 실제로 건 필터. min_store_count 는 기본값이 있어 항상 활성.
        하위 쿼리 모델이 더한 필드(district_code·sort_by 등)는 필터가 아니므로 뺀다."""
        # MarketFilter 자체 필드 중 값이 None 도 빈 목록도 아닌 것만 고른다.
        return {k for k in MarketFilter.model_fields if getattr(self, k) not in (None, [])}


# 응답에 붙는 필터 적용 결과.
class FilterMeta(BaseModel):
    # 실제로 적용된 필터 이름들
    applied_filters: list[str]
    # 걸었지만 이 엔드포인트에선 적용 못 한 필터 이름들
    ignored_filters: list[str] = Field(description="이 엔드포인트의 데이터 단위로는 적용할 수 없어 무시된 필터")

    # 필터와 '이 엔드포인트가 지원하는 필터 목록'으로 메타를 만드는 생성 함수.
    @classmethod
    def of(cls, f: MarketFilter, supported: set[str]) -> FilterMeta:
        # 사용자가 건 필터들
        active = f.active_fields()
        # 지원하는 것은 applied, 나머지는 ignored 로 나눠 정렬해 담는다.
        return cls(applied_filters=sorted(active & supported), ignored_filters=sorted(active - supported))


# 항목 목록 + 필터 메타로 이뤄진 공통 응답 틀. ListResponse[RegionItem] 처럼 쓴다.
class ListResponse(BaseModel, Generic[T]):
    # 결과 항목들
    items: list[T]
    # 필터 적용 결과
    meta: FilterMeta
