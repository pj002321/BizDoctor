# [역할] 진단 라우트 — POST /api/diagnosis, GET /api/diagnosis/context, GET /api/diagnosis/{id} (F-DIA-01·07·08).
"""/api/diagnosis — 사업장 '진단 등급'(F-DIA)."""
# 타입 힌트를 늦게 평가한다.
from __future__ import annotations

# 타입에 부가정보를 붙이는 도구.
from typing import Annotated
# 진단 ID 타입 — 경로 변수가 UUID 형식이 아니면 422.
from uuid import UUID

# APIRouter: 라우트 묶음, Depends: 의존성, Query: 쿼리 파라미터, Response: 응답 헤더 조작용.
from fastapi import APIRouter, Depends, Query, Response
# DB 세션 타입.
from sqlalchemy.orm import Session

# 진단 모델·정책 검색기를 주입하는 의존성.
from app.api.deps import get_predictor, get_solution_finder
# DB 세션 의존성.
from app.core.db import get_db
# 진단 관련 요청·응답 스키마.
from app.schemas.diagnosis import (
    # /context 응답
    DiagnosisContextResponse,
    # /{id} 응답(공유 링크용, 매출 수치 제외)
    DiagnosisPublicView,
    # POST 요청 본문
    DiagnosisRequest,
)
# POST 응답 — F-RAG-04 신호 JSON.
from app.schemas.signal import SignalResponse
# 진단 로직을 담당하는 서비스.
from app.service import diagnosis_service

# /api/diagnosis 로 시작하는 라우트 묶음.
router = APIRouter(prefix="/api/diagnosis", tags=["diagnosis"])
# DB 세션을 주입받는다는 타입 별칭.
DB = Annotated[Session, Depends(get_db)]


# POST /api/diagnosis — 진단을 실행하고 신호 JSON 을 돌려준다.
@router.post("", response_model=SignalResponse, summary="진단 실행 (F-DIA-01~06 → F-RAG-04 신호 JSON)")
def diagnose(
    # 요청 본문(행정동·업종·3개월 매출). 형식이 틀리면 여기서 422.
    req: DiagnosisRequest,
    # 응답 헤더를 붙이기 위한 객체.
    response: Response,
    # DB 세션
    db: DB,
    # 진단 모델(없으면 None)
    predictor=Depends(get_predictor),
    # 정책 검색기(없으면 None)
    finder=Depends(get_solution_finder),
):
    # 서비스가 진단을 실행하고 (진단 ID, 신호 JSON)을 돌려준다.
    diagnosis_id, signal = diagnosis_service.run_diagnosis(db, req, predictor, finder)
    # 본문은 스펙의 신호 JSON 그대로 두고, 재조회 ID 는 헤더로 준다.
    response.headers["Location"] = f"/api/diagnosis/{diagnosis_id}"
    # 프론트가 쉽게 꺼내 쓰도록 ID 만 담은 헤더도 붙인다.
    response.headers["X-Diagnosis-Id"] = str(diagnosis_id)
    # 신호 JSON 을 본문으로 돌려준다.
    return signal


# ⚠ /context 는 /{diagnosis_id} 보다 먼저 선언한다. 순서가 바뀌어도 UUID 타입이라
# 'context' 가 422 로 떨어질 뿐 잘못 매칭되진 않지만, 의도를 코드 순서로도 드러낸다.
@router.get("/context", response_model=DiagnosisContextResponse, summary="상권 대비 위치 (F-DIA-07)")
def context(
    # DB 세션
    db: DB,
    # 행정동 코드(숫자 8~10자리)
    district_code: Annotated[str, Query(pattern=r"^\d{8,10}$")],
    # 업종 코드(CS + 숫자 6자리)
    industry_code: Annotated[str, Query(pattern=r"^CS\d{6}$")],
):
    # 서비스가 같은 업종 분포에서의 위치를 계산해 돌려준다.
    return diagnosis_service.get_context(db, district_code, industry_code)


# GET /api/diagnosis/{diagnosis_id} — 저장된 진단을 공유 링크로 다시 본다.
@router.get("/{diagnosis_id}", response_model=DiagnosisPublicView, summary="진단 결과 재조회 (F-DIA-08)")
def get_diagnosis(diagnosis_id: UUID, db: DB):
    # 서비스가 만료 여부를 확인하고 공개용 결과를 돌려준다.
    return diagnosis_service.get_public_view(db, diagnosis_id)
