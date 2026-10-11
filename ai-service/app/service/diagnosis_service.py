# [역할] 진단 서비스 — 입력 정규화·정적 피처 조인·폴백, 모델/검색 호출, 결과 저장, 맥락·재조회 로직을 조율한다.
"""사업장 진단(F-DIA). 이번 범위는 입력부(F-DIA-01·02)와 맥락·재조회(F-DIA-07·08).

추론(F-DIA-03~06)과 정책 검색(F-RAG-03)은 아래 두 포트 뒤에 붙는다. 붙기 전에는
POST /api/diagnosis 가 503 을 돌려준다 — 보정(F-DIA-04) 없는 확률이 새 나가지 않게.
"""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 경고·정보 로그를 남기기 위한 모듈.
import logging
# 값만 담는 클래스를 만드는 데코레이터.
from dataclasses import dataclass
# UTC 시간대, 현재 시각, 시간 간격.
from datetime import UTC, datetime, timedelta
# '이런 메서드를 가진 객체'를 뜻하는 인터페이스 타입.
from typing import Protocol
# UUID 타입과 무작위 UUID 생성 함수.
from uuid import UUID, uuid4

# DB 세션 타입.
from sqlalchemy.orm import Session

# 설정값.
from app.core import config
# 분기 표기 변환.
from app.domain import quarter as qt
# 히스토그램 계산.
from app.domain.distribution import histogram
# '상위 N%' 계산.
from app.domain.market_signal import top_percent
# 유형 타입, 유형→등급, 등급→테마.
from app.domain.risk_type import RiskType, level_of, theme_of
# 매출 지수 변환 두 가지.
from app.domain.sales_index import index_to_model_sequence, to_sales_index
# 진단 저장·피처 조회·기준표 조회 저장소.
from app.repo import diagnosis_repo, feature_repo, market_repo
# 진단 관련 스키마들.
from app.schemas.diagnosis import (
    # 맥락 응답
    DiagnosisContextResponse,
    # 공유 링크 응답
    DiagnosisPublicView,
    # 진단 요청
    DiagnosisRequest,
    # 히스토그램 구간
    DistributionBin,
    # 모델 직전 입력
    PreparedInput,
    # 정적 피처
    StaticFeatures,
)
# 신호 JSON 과 정책자금 한 건.
from app.schemas.signal import SignalResponse, Solution
# 서비스 예외들.
from app.service.errors import (
    # 410
    GoneError,
    # 422
    InvalidInputError,
    # 404
    NotFoundError,
    # 503
    NotReadyError,
)

# 이 모듈 이름으로 로거를 만든다.
log = logging.getLogger(__name__)

# 정적 피처 중 숫자 값 4개의 이름 — 폴백을 돌릴 대상.
FEATURE_FIELDS = ("closure_pctl_in_industry", "closure_rate", "open_rate", "franchise_ratio")


# --- 포트: 모델·RAG 가 구현한다 ------------------------------------------------
# 모델이 돌려줘야 하는 예측 결과(불변).
@dataclass(frozen=True)
class Prediction:
    # 예측된 원인 유형
    risk_type: RiskType
    # 그 유형의 확률
    risk_type_confidence: float  # 사전확률 보정(F-DIA-04) 후 값이어야 한다
    # 위험 점수(0~100)
    score: int                   # F-DIA-06


# 진단 모델이 지켜야 할 모양: predict(prepared) → Prediction.
class RiskPredictor(Protocol):
    # 모델 직전 입력을 받아 예측을 돌려준다.
    def predict(self, prepared: PreparedInput) -> Prediction: ...


# 정책 검색기가 지켜야 할 모양: find(유형, top_k) → 정책자금 목록.
class SolutionFinder(Protocol):
    # 유형에 맞는 정책자금을 최대 top_k 건 돌려준다.
    def find(self, risk_type: RiskType, top_k: int = 3) -> list[Solution]: ...


# --- F-DIA-02 ----------------------------------------------------------------
# 정적 피처를 가져올 기준 분기(DB 형식)를 정한다.
def _base_quarter(db: Session) -> str:
    # 설정에 기준 분기가 지정돼 있으면
    if config.FEATURE_BASE_QUARTER:
        # 그것을 DB 형식으로 바꿔 쓴다.
        return qt.api_to_db(config.FEATURE_BASE_QUARTER)
    # 아니면 DB 의 최신 분기를 조회한다.
    q = feature_repo.latest_quarter(db)
    # 데이터가 하나도 없으면
    if q is None:
        # 503 으로 알린다.
        raise NotReadyError("상권 패널 데이터가 적재되지 않았습니다.")
    # 최신 분기를 돌려준다.
    return q


# 행정동·업종으로 정적 피처를 조회하고, 빠진 값은 폴백으로 채운다.
def load_static_features(db: Session, district_code: str, industry_code: str) -> StaticFeatures:
    # 행정동 기준표에서 찾는다.
    district = market_repo.fetch_district(db, district_code)
    # 없는 행정동이면
    if district is None:
        # 422(입력이 데이터와 안 맞음).
        raise InvalidInputError(f"알 수 없는 행정동 코드입니다: {district_code}")
    # 업종 기준표에서 찾는다.
    industry = market_repo.fetch_industry(db, industry_code)
    # 없는 업종이면
    if industry is None:
        # 422.
        raise InvalidInputError(f"알 수 없는 업종 코드입니다: {industry_code}")

    # 적용한 폴백을 기록할 목록.
    fallbacks: list[str] = []
    # 업종의 KOSIS 산업대분류.
    kosis = industry["kosis_industry1"]
    # 매핑이 안 돼 있으면(NULL)
    if not kosis:
        # 경고 로그를 남긴다.
        log.warning("업종 KOSIS 매핑 실패 → '%s' 폴백: %s(%s)",
                    # 폴백 값, 업종 이름, 업종 코드
                    config.KOSIS_FALLBACK_INDUSTRY, industry["industry_name"], industry_code)
        # '전산업'으로 대체한다.
        kosis = config.KOSIS_FALLBACK_INDUSTRY
        # 폴백 기록을 남긴다.
        fallbacks.append(f"kosis_industry1:{config.KOSIS_FALLBACK_INDUSTRY}")

    # 기준 분기를 정한다.
    quarter = _base_quarter(db)
    # 해당 행정동×업종×분기 피처를 조회한다(없으면 빈 딕셔너리).
    cell = feature_repo.cell_features(db, district_code, industry_code, quarter) or {}
    # 셀 자체가 없으면(그 동네에 해당 업종 점포가 없음)
    if not cell:
        # 업종 중앙값 폴백을 썼다고 기록한다.
        fallbacks.append("cell_missing:industry_median")

    # 피처 4개 값을 꺼낸다(셀이 없으면 전부 None).
    values = {k: cell.get(k) for k in FEATURE_FIELDS}
    # 값이 비어 있는 피처 이름들.
    missing = [k for k, v in values.items() if v is None]
    # 하나라도 비었으면
    if missing:
        # 셀이 없거나(그 동네에 해당 업종 점포 없음) 값이 비었으면 같은 업종·분기 서울 중앙값.
        # 학습 때도 결측은 중앙값으로 채웠다(train_risk_model.py fillna(median)).
        med = feature_repo.industry_medians(db, industry_code, quarter)
        # 빈 피처마다
        for k in missing:
            # 중앙값조차 없으면(업종 데이터 자체가 없음)
            if med.get(k) is None:
                # 진단할 수 없다고 422 로 알린다.
                raise InvalidInputError(f"해당 업종의 {qt.db_to_api(quarter)} 상권 데이터가 없어 진단할 수 없습니다.")
            # 중앙값으로 채운다.
            values[k] = med[k]
            # 셀은 있는데 이 값만 비었던 경우
            if cell:
                # 어느 피처를 채웠는지 기록한다.
                fallbacks.append(f"{k}:industry_median")
        # 폴백 내역을 정보 로그로 남긴다.
        log.info("정적 피처 폴백 %s (%s × %s, %s)", fallbacks, district_code, industry_code, quarter)

    # 정적 피처 객체를 만들어 돌려준다.
    return StaticFeatures(base_quarter=qt.db_to_api(quarter), kosis_industry1=kosis, fallbacks=fallbacks, **values)


# --- F-DIA-01 + 02 ------------------------------------------------------------
# 요청을 모델 직전 입력으로 바꾼다(지수 변환 + 정적 피처).
def prepare_input(db: Session, req: DiagnosisRequest) -> PreparedInput:
    # 실금액을 1개월차=100 지수로 바꾼다.
    index = to_sales_index(req.monthly_sales, months=config.SALES_MONTHS, max_amount=config.SALES_AMOUNT_MAX)
    # 이 줄 이후로 실금액(req.monthly_sales)을 쓰지 않는다(F-SYS-05).
    return PreparedInput(
        # 행정동 코드
        district_code=req.district_code,
        # 업종 코드
        industry_code=req.industry_code,
        # 저장용 지수
        sales_index=index,
        # 모델 입력용 시퀀스(1개월차=1.0)
        model_sequence=index_to_model_sequence(index),
        # 정적 피처(폴백 포함)
        features=load_static_features(db, req.district_code, req.industry_code),
    )


# 진단 전체 흐름: 입력 준비 → 예측 → 정책 검색 → 신호 JSON → 저장.
def run_diagnosis(
    # DB 세션
    db: Session,
    # 요청 본문
    req: DiagnosisRequest,
    # 진단 모델(없으면 None)
    predictor: RiskPredictor | None,
    # 정책 검색기(없으면 None)
    finder: SolutionFinder | None,
) -> tuple[UUID, SignalResponse]:
    # 입력을 준비한다(여기서 입력 오류가 먼저 걸러진다).
    prepared = prepare_input(db, req)
    # 모델이나 검색기가 아직 없으면
    if predictor is None or finder is None:
        # 503 으로 알린다.
        raise NotReadyError("진단 모델 또는 정책 검색 인덱스가 아직 연결되지 않았습니다.")

    # 모델로 예측한다.
    pred = predictor.predict(prepared)
    # 유형으로 진단 등급을 정한다.
    level = level_of(pred.risk_type)
    # 신호 JSON 을 만든다(스키마가 등급·테마 일치를 다시 검증한다).
    signal = SignalResponse(
        # 진단 등급
        risk_level=level,
        # 추정 원인 유형
        risk_type=pred.risk_type,
        # 유형 확률
        risk_type_confidence=pred.risk_type_confidence,
        # 위험 점수
        score=pred.score,
        # 화면 테마
        visual_theme=theme_of(level),
        # 유형에 맞는 정책자금 검색
        solutions=finder.find(pred.risk_type),
    )

    # 현재 시각(UTC).
    now = datetime.now(UTC)
    # 새 진단 ID 를 무작위로 만든다.
    diagnosis_id = uuid4()
    # 결과를 DB 에 저장한다(실금액은 넘기지 않는다).
    diagnosis_repo.save(
        # DB 세션
        db,
        # 진단 ID
        diagnosis_id=diagnosis_id,
        # 행정동 코드
        district_code=prepared.district_code,
        # 업종 코드
        industry_code=prepared.industry_code,
        # 매출 지수
        sales_index=prepared.sales_index,
        # 신호 JSON 을 JSON 호환 딕셔너리로 바꿔 저장
        signal=signal.model_dump(mode="json"),
        # 폴백이 하나라도 있었는지
        feature_fallback=bool(prepared.features.fallbacks),
        # 생성 시각
        created_at=now,
        # 만료 시각 = 지금 + 24시간
        expires_at=now + timedelta(hours=config.DIAGNOSIS_TTL_HOURS),  # 로그인 연동 전까지는 전부 임시
    )
    # 진단 ID 와 신호 JSON 을 돌려준다.
    return diagnosis_id, signal


# --- F-DIA-07 -----------------------------------------------------------------
# 같은 업종 서울 행정동들 사이에서 이 행정동의 위치를 계산한다.
def get_context(db: Session, district_code: str, industry_code: str) -> DiagnosisContextResponse:
    # 행정동 정보를 가져온다.
    district = market_repo.fetch_district(db, district_code)
    # 없으면
    if district is None:
        # 404.
        raise NotFoundError(f"행정동을 찾을 수 없습니다: {district_code}")
    # 업종 정보를 가져온다.
    industry = market_repo.fetch_industry(db, industry_code)
    # 없으면
    if industry is None:
        # 404.
        raise NotFoundError(f"업종을 찾을 수 없습니다: {industry_code}")

    # 기준 분기를 정한다.
    quarter = _base_quarter(db)
    # 이 행정동×업종의 피처를 가져온다.
    cell = feature_repo.cell_features(db, district_code, industry_code, quarter)
    # 셀이 없거나 percentile 이 없으면
    if cell is None or cell["closure_pctl_in_industry"] is None:
        # 위치를 계산할 수 없으니 404.
        raise NotFoundError(f"{district['district_name']} {industry['industry_name']} 의 {qt.db_to_api(quarter)} 상권 데이터가 없습니다.")

    # 업종 내 percentile.
    pctl = cell["closure_pctl_in_industry"]
    # '상위 N%' 의 N.
    top = top_percent(pctl)
    # 같은 업종·분기 행정동들의 폐업률(점포 5개 이상만).
    rates = feature_repo.industry_closure_rates(db, industry_code, quarter, config.MIN_STORE_COUNT_DEFAULT)
    # 20구간 히스토그램을 만들고(100% 초과는 마지막 구간) 스키마로 바꾼다.
    bins = [DistributionBin(lower=lo, upper=hi, count=n) for lo, hi, n in histogram(rates, bins=20, upper_clip=100.0)]
    # '진단 등급'이 아니라 동네 상권 위치다(F-SYS-01) — 문구에 '상권'을 명시한다.
    message = f"서울 {industry['industry_name']} 상권 중 {district['district_name']}은(는) 폐업 위험 상위 {top}%입니다."
    # 응답을 만들어 돌려준다.
    return DiagnosisContextResponse(
        # 행정동 코드
        district_code=district_code,
        # 행정동 이름
        district_name=district["district_name"],
        # 업종 코드
        industry_code=industry_code,
        # 업종 이름
        industry_name=industry["industry_name"],
        # 기준 분기(API 형식)
        quarter=qt.db_to_api(quarter),
        # percentile
        closure_pctl_in_industry=pctl,
        # 상위 N%
        top_percent=top,
        # 이 행정동의 폐업률
        closure_rate=cell["closure_rate"],
        # 분포
        distribution=bins,
        # 화면 문구
        message=message,
    )


# --- F-DIA-08 -----------------------------------------------------------------
# 저장된 진단을 공유 링크용으로 돌려준다. now 는 테스트에서 시각을 고정할 때 쓴다.
def get_public_view(db: Session, diagnosis_id: UUID, now: datetime | None = None) -> DiagnosisPublicView:
    # ID 로 저장된 진단을 찾는다.
    row = diagnosis_repo.get(db, diagnosis_id)
    # 없으면
    if row is None:
        # 404.
        raise NotFoundError("진단 결과를 찾을 수 없습니다.")
    # 기준 시각이 없으면 현재 시각(UTC)을 쓴다.
    now = now or datetime.now(UTC)
    # 만료 시각이 있고 이미 지났으면
    if row["expires_at"] is not None and row["expires_at"] <= now:
        # 410.
        raise GoneError("공유 링크가 만료되었습니다.")
    # 저장된 신호 JSON 을 다시 스키마로 읽어 검증한다.
    s = SignalResponse.model_validate(row["signal"])
    # score 와 매출 지수는 링크 소지자에게 비공개(F-DIA-08)
    return DiagnosisPublicView(
        # 진단 ID
        diagnosis_id=row["diagnosis_id"],
        # 진단 등급
        risk_level=s.risk_level,
        # 추정 원인
        risk_type=s.risk_type,
        # 유형 확률
        risk_type_confidence=s.risk_type_confidence,
        # 화면 테마
        visual_theme=s.visual_theme,
        # 정책자금
        solutions=s.solutions,
        # 생성 시각
        created_at=row["created_at"],
        # 만료 시각
        expires_at=row["expires_at"],
    )
