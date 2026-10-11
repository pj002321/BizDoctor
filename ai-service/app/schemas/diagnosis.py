# [역할] 진단 스키마 — 진단 입력 검증, 정적 피처, 모델 직전 입력, 상권 대비 위치 응답, 공유 링크 응답 형태.
"""사업장 진단(F-DIA) 입출력."""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 시각 타입.
from datetime import datetime
# 진단 ID 타입.
from uuid import UUID

# 스키마 기반 클래스·설정·필드 옵션·필드 단위 검증.
from pydantic import BaseModel, ConfigDict, Field, field_validator

# 개월 수·금액 상한 설정.
from app.core import config
# 진단 등급·유형·테마 타입.
from app.domain.risk_type import RiskLevel, RiskType, VisualTheme
# 매출 → 지수 변환(입력 검증에 재사용).
from app.domain.sales_index import to_sales_index
# 정책자금 한 건 스키마.
from app.schemas.signal import Solution


# POST /api/diagnosis 요청 본문.
class DiagnosisRequest(BaseModel):  # F-DIA-01
    # 정의 안 된 필드는 받지 않는다.
    model_config = ConfigDict(extra="forbid")

    # 행정동 코드: 숫자 8~10자리.
    district_code: str = Field(pattern=r"^\d{8,10}$", description="행정동 코드", examples=["11440660"])
    # 업종 코드: 'CS' + 숫자 6자리.
    industry_code: str = Field(pattern=r"^CS\d{6}$", description="서비스 업종 코드", examples=["CS100001"])
    # repr=False: 실금액이 로그·예외 메시지로 새지 않게(F-SYS-05)
    monthly_sales: list[float] = Field(
        # 최소 3개
        min_length=config.SALES_MONTHS,
        # 최대 3개
        max_length=config.SALES_MONTHS,
        # 객체를 출력해도 이 필드는 보이지 않게
        repr=False,
        # 문서 설명
        description="최근 3개월 월매출 실금액(원), 오래된 달부터. 서버에 저장하지 않는다.",
        # 문서 예시
        examples=[[12_000_000, 11_000_000, 9_500_000]],
    )

    # monthly_sales 필드 값이 들어올 때 추가 검증한다.
    @field_validator("monthly_sales")
    # 클래스 메서드 형태로 정의한다(Pydantic 규칙).
    @classmethod
    def _convertible(cls, v: list[float]) -> list[float]:
        # 지수로 바꿔 보고, 안 되면(0·음수·NaN 등) 예외가 나서 422 가 된다.
        to_sales_index(v, months=config.SALES_MONTHS, max_amount=config.SALES_AMOUNT_MAX)  # 실패 시 ValueError → 422
        # 통과하면 원래 값을 그대로 둔다.
        return v


# 모델에 들어가는 정적 피처 묶음(내부용).
class StaticFeatures(BaseModel):  # F-DIA-02 — 내부용, 응답에 그대로 내보내지 않는다
    # 피처를 가져온 분기(예: 2025Q4)
    base_quarter: str
    # 업종 내 폐업률 percentile
    closure_pctl_in_industry: float
    # 폐업률
    closure_rate: float
    # 개업률
    open_rate: float
    # 프랜차이즈 비중
    franchise_ratio: float
    # KOSIS 산업대분류(모델 one-hot 입력)
    kosis_industry1: str
    # 어떤 폴백이 쓰였는지 기록
    fallbacks: list[str] = Field(default_factory=list, description="적용된 폴백 목록(로그·저장용)")


# 모델에 넣기 직전의 입력 전체.
class PreparedInput(BaseModel):
    """모델에 들어가기 직전 상태. 실금액은 여기 없다."""

    # 행정동 코드
    district_code: str
    # 업종 코드
    industry_code: str
    # 저장용 지수
    sales_index: list[float]          # 1개월차 = 100
    # 모델 입력 시퀀스
    model_sequence: list[list[float]]  # (3, 1), 1개월차 = 1.0
    # 정적 피처
    features: StaticFeatures


# 히스토그램 구간 하나.
class DistributionBin(BaseModel):
    # 구간 하한
    lower: float
    # 구간 상한
    upper: float
    # 구간에 속한 행정동 수
    count: int


# GET /api/diagnosis/context 응답.
class DiagnosisContextResponse(BaseModel):  # F-DIA-07
    # 행정동 코드
    district_code: str
    # 행정동 이름
    district_name: str
    # 업종 코드
    industry_code: str
    # 업종 이름
    industry_name: str
    # 기준 분기
    quarter: str
    # 이 행정동의 업종 내 percentile
    closure_pctl_in_industry: float = Field(description="같은 업종·분기 내 폐업률 percentile(0~1, 높을수록 위험)")
    # '상위 N%' 의 N
    top_percent: int = Field(description="'상위 N%' 의 N")
    # 이 행정동의 폐업률
    closure_rate: float | None
    # 서울 전체 분포
    distribution: list[DistributionBin] = Field(description="같은 업종·분기 서울 행정동들의 폐업률 분포")
    # 화면에 보여줄 문구
    message: str


# GET /api/diagnosis/{id} 응답 — 공유 링크로 보는 사람에게 보여줄 내용.
class DiagnosisPublicView(BaseModel):  # F-DIA-08 — 링크 소지자용. 매출 관련 수치(지수·score)는 비공개
    # 진단 ID
    diagnosis_id: UUID
    # 진단 등급
    risk_level: RiskLevel
    # 추정 원인 유형
    risk_type: RiskType
    # 유형 확률
    risk_type_confidence: float
    # 화면 테마
    visual_theme: VisualTheme
    # 추천 정책자금
    solutions: list[Solution]
    # 생성 시각
    created_at: datetime
    # 만료 시각(없으면 영구)
    expires_at: datetime | None
