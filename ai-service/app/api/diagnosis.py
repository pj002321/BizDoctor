"""/api/diagnosis — 사업장 '진단 등급'(F-DIA)."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_predictor, get_solution_finder
from app.core.db import get_db
from app.schemas.diagnosis import (
    DiagnosisContextResponse,
    DiagnosisPublicView,
    DiagnosisRequest,
)
from app.schemas.signal import SignalResponse
from app.service import diagnosis_service

router = APIRouter(prefix="/api/diagnosis", tags=["diagnosis"])
DB = Annotated[Session, Depends(get_db)]


@router.post("", response_model=SignalResponse, summary="진단 실행 (F-DIA-01~06 → F-RAG-04 신호 JSON)")
def diagnose(
    req: DiagnosisRequest,
    response: Response,
    db: DB,
    predictor=Depends(get_predictor),
    finder=Depends(get_solution_finder),
):
    diagnosis_id, signal = diagnosis_service.run_diagnosis(db, req, predictor, finder)
    response.headers["Location"] = f"/api/diagnosis/{diagnosis_id}"
    response.headers["X-Diagnosis-Id"] = str(diagnosis_id)
    return signal


@router.get("/context", response_model=DiagnosisContextResponse, summary="상권 대비 위치 (F-DIA-07)")
def context(
    db: DB,
    district_code: Annotated[str, Query(pattern=r"^\d{8,10}$")],
    industry_code: Annotated[str, Query(pattern=r"^CS\d{6}$")],
):
    return diagnosis_service.get_context(db, district_code, industry_code)


@router.get("/{diagnosis_id}", response_model=DiagnosisPublicView, summary="진단 결과 재조회 (F-DIA-08)")
def get_diagnosis(diagnosis_id: UUID, db: DB):
    return diagnosis_service.get_public_view(db, diagnosis_id)
