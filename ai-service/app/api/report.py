"""POST / api / report: AI 진단 리포트"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.diagnosis import ReportRequest
from app.service import report_service

router = APIRouter(prefix="/api/report", tags=["report"])
DB = Annotated[Session, Depends(get_db)]


@router.post("",response_class=PlainTextResponse, summary="AI 진단 리포트")
def create_report(req: ReportRequest, db: DB) -> PlainTextResponse:
    """창구: 진단 번호를 받아 완성한 리포트를 돌려준다."""
    report, outcome = report_service.make_report(db, req.diagnosis_id)
    return PlainTextResponse(report, headers={"X-Report-Outcome": outcome})