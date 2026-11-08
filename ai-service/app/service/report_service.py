"""AI 진단 리포트"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.report_context import DISCLAIMER
from app.graph.graph import report_graph
from app.repo import diagnosis_repo
from app.service.errors import NotFoundError


def make_report(db: Session, diagnosis_id: UUID) -> tuple[str,str]:
    """저장된 진단을 꺼내 리포트 그래프에 넣는다.
    LLM이 쓴 리포트 -> 면책 문구 붙임 / fallback -> 이미 들어있음 / no_docs -> 그대로"""
    row = diagnosis_repo.get(db, diagnosis_id)
    if row is None:
        raise NotFoundError("진단 결과를 찾을 수 없습니다.")
    state = report_graph.invoke({"signal": row["signal"]})
    report = state["report"]
    if state["outcome"] in ("passed", "regenerated"):
        report += "\n\n" + DISCLAIMER
    return report, state["outcome"]

