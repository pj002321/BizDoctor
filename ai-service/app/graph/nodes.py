"""리포트 그래프 노드. 상태를 받아서 바뀐 필드만 dict로 반환"""

from app.domain.report_context import build_context
from app.domain.signal import RISK_TYPE_QUERY
from app.graph.state import ReportState
from app.knowledge.retrieve import retrieve


def retrieve_docs(state: ReportState) -> dict:
    """공고 찾아오기: 검색어가 없으면 유형별로 질의를 함"""
    rt = state["signal"]["risk_type"]
    query = state.get("query") or RISK_TYPE_QUERY[rt]
    return {"query": query, "docs": retrieve(query,rt)}


def grade_docs(state: ReportState) -> dict:
    """상담에 맞지 않는 공고 빼기: 진단 유형 태그가 붙은 공고만 남김"""
    rt = state["signal"]["risk_type"]
    docs = [(d,s) for d, s in state["docs"] 
            if state.get("relaxed") or rt in (d["risk_type_tags"] or [])]
    return {"docs": docs, "context": build_context(state["signal"], [d for d, _ in docs])}


def route_after_grade(state: ReportState) -> str:
    """다음에 어디로 보낼지
    공고 있음 -> generate , 공고 없음 -> rewrite_query, 다시 찾아도 0건 -> no_docs"""
    if state["docs"]:
        return "generate"
    return "no_docs" if state.get("relaxed") else "rewrite_query"