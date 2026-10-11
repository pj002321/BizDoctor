"""사업장 진단(F-DIA) 입출력."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core import config
from app.domain.risk_type import RiskLevel, RiskType, VisualTheme
from app.domain.sales_index import to_sales_index
from app.schemas.signal import Solution


class DiagnosisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    district_code: str = Field(pattern=r"^\d{8,10}$", description="행정동 코드", examples=["11440660"])
    industry_code: str = Field(pattern=r"^CS\d{6}$", description="서비스 업종 코드", examples=["CS100001"])
    monthly_sales: list[float] = Field(
        min_length=config.SALES_MONTHS,
        max_length=config.SALES_MONTHS,
        repr=False,
        description="최근 3개월 월매출 실금액(원), 오래된 달부터. 서버에 저장하지 않는다.",
        examples=[[12_000_000, 11_000_000, 9_500_000]],
    )

    @field_validator("monthly_sales")
    @classmethod
    def _convertible(cls, v: list[float]) -> list[float]:
        to_sales_index(v, months=config.SALES_MONTHS, max_amount=config.SALES_AMOUNT_MAX)
        return v


class StaticFeatures(BaseModel):
    base_quarter: str
    closure_pctl_in_industry: float
    closure_rate: float
    open_rate: float
    franchise_ratio: float
    kosis_industry1: str
    fallbacks: list[str] = Field(default_factory=list, description="적용된 폴백 목록(로그·저장용)")


class PreparedInput(BaseModel):
    """모델에 들어가기 직전 상태. 실금액은 여기 없다."""

    district_code: str
    industry_code: str
    sales_index: list[float]
    model_sequence: list[list[float]]
    features: StaticFeatures


class DistributionBin(BaseModel):
    lower: float
    upper: float
    count: int


class DiagnosisContextResponse(BaseModel):
    district_code: str
    district_name: str
    industry_code: str
    industry_name: str
    quarter: str
    closure_pctl_in_industry: float = Field(description="같은 업종·분기 내 폐업률 percentile(0~1, 높을수록 위험)")
    top_percent: int = Field(description="'상위 N%' 의 N")
    closure_rate: float | None
    distribution: list[DistributionBin] = Field(description="같은 업종·분기 서울 행정동들의 폐업률 분포")
    message: str


class DiagnosisPublicView(BaseModel):
    diagnosis_id: UUID
    risk_level: RiskLevel
    risk_type: RiskType
    risk_type_confidence: float
    visual_theme: VisualTheme
    solutions: list[Solution]
    created_at: datetime
    expires_at: datetime | None
