"""사업장 진단(F-DIA). 이번 범위는 입력부(F-DIA-01·02)와 맥락·재조회(F-DIA-07·08).

추론(F-DIA-03~06)과 정책 검색(F-RAG-03)은 아래 두 포트 뒤에 붙는다. 붙기 전에는
POST /api/diagnosis 가 503 을 돌려준다 — 보정(F-DIA-04) 없는 확률이 새 나가지 않게.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core import config
from app.domain import quarter as qt
from app.domain.distribution import histogram
from app.domain.market_signal import top_percent
from app.domain.risk_type import RiskType, level_of, theme_of
from app.domain.sales_index import index_to_model_sequence, to_sales_index
from app.repo import diagnosis_repo, feature_repo, market_repo
from app.schemas.diagnosis import (
    DiagnosisContextResponse,
    DiagnosisPublicView,
    DiagnosisRequest,
    DistributionBin,
    PreparedInput,
    StaticFeatures,
)
from app.schemas.signal import SignalResponse, Solution
from app.service.errors import (
    GoneError,
    InvalidInputError,
    NotFoundError,
    NotReadyError,
)

log = logging.getLogger(__name__)

FEATURE_FIELDS = ("closure_pctl_in_industry", "closure_rate", "open_rate", "franchise_ratio")


@dataclass(frozen=True)
class Prediction:
    risk_type: RiskType
    risk_type_confidence: float
    score: int


class RiskPredictor(Protocol):
    def predict(self, prepared: PreparedInput) -> Prediction: ...


class SolutionFinder(Protocol):
    def find(self, risk_type: RiskType, top_k: int = 3) -> list[Solution]: ...


def _base_quarter(db: Session) -> str:
    if config.FEATURE_BASE_QUARTER:
        return qt.api_to_db(config.FEATURE_BASE_QUARTER)
    q = feature_repo.latest_quarter(db)
    if q is None:
        raise NotReadyError("상권 패널 데이터가 적재되지 않았습니다.")
    return q


def load_static_features(db: Session, district_code: str, industry_code: str) -> StaticFeatures:
    district = market_repo.fetch_district(db, district_code)
    if district is None:
        raise InvalidInputError(f"알 수 없는 행정동 코드입니다: {district_code}")
    industry = market_repo.fetch_industry(db, industry_code)
    if industry is None:
        raise InvalidInputError(f"알 수 없는 업종 코드입니다: {industry_code}")

    fallbacks: list[str] = []
    kosis = industry["kosis_industry1"]
    if not kosis:
        log.warning("업종 KOSIS 매핑 실패 → '%s' 폴백: %s(%s)",
                    config.KOSIS_FALLBACK_INDUSTRY, industry["industry_name"], industry_code)
        kosis = config.KOSIS_FALLBACK_INDUSTRY
        fallbacks.append(f"kosis_industry1:{config.KOSIS_FALLBACK_INDUSTRY}")

    quarter = _base_quarter(db)
    cell = feature_repo.cell_features(db, district_code, industry_code, quarter) or {}
    if not cell:
        fallbacks.append("cell_missing:industry_median")

    values = {k: cell.get(k) for k in FEATURE_FIELDS}
    missing = [k for k, v in values.items() if v is None]
    if missing:
        med = feature_repo.industry_medians(db, industry_code, quarter)
        for k in missing:
            if med.get(k) is None:
                raise InvalidInputError(f"해당 업종의 {qt.db_to_api(quarter)} 상권 데이터가 없어 진단할 수 없습니다.")
            values[k] = med[k]
            if cell:
                fallbacks.append(f"{k}:industry_median")
        log.info("정적 피처 폴백 %s (%s × %s, %s)", fallbacks, district_code, industry_code, quarter)

    return StaticFeatures(base_quarter=qt.db_to_api(quarter), kosis_industry1=kosis, fallbacks=fallbacks, **values)


def prepare_input(db: Session, req: DiagnosisRequest) -> PreparedInput:
    index = to_sales_index(req.monthly_sales, months=config.SALES_MONTHS, max_amount=config.SALES_AMOUNT_MAX)
    return PreparedInput(
        district_code=req.district_code,
        industry_code=req.industry_code,
        sales_index=index,
        model_sequence=index_to_model_sequence(index),
        features=load_static_features(db, req.district_code, req.industry_code),
    )


def run_diagnosis(
    db: Session,
    req: DiagnosisRequest,
    predictor: RiskPredictor | None,
    finder: SolutionFinder | None,
) -> tuple[UUID, SignalResponse]:
    prepared = prepare_input(db, req)
    if predictor is None or finder is None:
        raise NotReadyError("진단 모델 또는 정책 검색 인덱스가 아직 연결되지 않았습니다.")

    pred = predictor.predict(prepared)
    level = level_of(pred.risk_type)
    signal = SignalResponse(
        risk_level=level,
        risk_type=pred.risk_type,
        risk_type_confidence=pred.risk_type_confidence,
        score=pred.score,
        visual_theme=theme_of(level),
        solutions=finder.find(pred.risk_type),
    )

    now = datetime.now(UTC)
    diagnosis_id = uuid4()
    diagnosis_repo.save(
        db,
        diagnosis_id=diagnosis_id,
        district_code=prepared.district_code,
        industry_code=prepared.industry_code,
        sales_index=prepared.sales_index,
        signal=signal.model_dump(mode="json"),
        feature_fallback=bool(prepared.features.fallbacks),
        created_at=now,
        expires_at=now + timedelta(hours=config.DIAGNOSIS_TTL_HOURS),
    )
    return diagnosis_id, signal


def get_context(db: Session, district_code: str, industry_code: str) -> DiagnosisContextResponse:
    district = market_repo.fetch_district(db, district_code)
    if district is None:
        raise NotFoundError(f"행정동을 찾을 수 없습니다: {district_code}")
    industry = market_repo.fetch_industry(db, industry_code)
    if industry is None:
        raise NotFoundError(f"업종을 찾을 수 없습니다: {industry_code}")

    quarter = _base_quarter(db)
    cell = feature_repo.cell_features(db, district_code, industry_code, quarter)
    if cell is None or cell["closure_pctl_in_industry"] is None:
        raise NotFoundError(f"{district['district_name']} {industry['industry_name']} 의 {qt.db_to_api(quarter)} 상권 데이터가 없습니다.")

    pctl = cell["closure_pctl_in_industry"]
    top = top_percent(pctl)
    rates = feature_repo.industry_closure_rates(db, industry_code, quarter, config.MIN_STORE_COUNT_DEFAULT)
    bins = [DistributionBin(lower=lo, upper=hi, count=n) for lo, hi, n in histogram(rates, bins=20, upper_clip=100.0)]
    message = f"서울 {industry['industry_name']} 상권 중 {district['district_name']}은(는) 폐업 위험 상위 {top}%입니다."
    return DiagnosisContextResponse(
        district_code=district_code,
        district_name=district["district_name"],
        industry_code=industry_code,
        industry_name=industry["industry_name"],
        quarter=qt.db_to_api(quarter),
        closure_pctl_in_industry=pctl,
        top_percent=top,
        closure_rate=cell["closure_rate"],
        distribution=bins,
        message=message,
    )


def get_public_view(db: Session, diagnosis_id: UUID, now: datetime | None = None) -> DiagnosisPublicView:
    row = diagnosis_repo.get(db, diagnosis_id)
    if row is None:
        raise NotFoundError("진단 결과를 찾을 수 없습니다.")
    now = now or datetime.now(UTC)
    if row["expires_at"] is not None and row["expires_at"] <= now:
        raise GoneError("공유 링크가 만료되었습니다.")
    s = SignalResponse.model_validate(row["signal"])
    return DiagnosisPublicView(
        diagnosis_id=row["diagnosis_id"],
        risk_level=s.risk_level,
        risk_type=s.risk_type,
        risk_type_confidence=s.risk_type_confidence,
        visual_theme=s.visual_theme,
        solutions=s.solutions,
        created_at=row["created_at"],
        expires_at=row["expires_at"],
    )
