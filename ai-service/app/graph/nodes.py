"""리포트 그래프 노드. 상태를 받아서 바뀐 필드만 dict로 반환"""

from app.domain.report_context import build_context
from app.domain.signal import RISK_TYPE_QUERY
from app.graph.state import ReportState
from app.knowledge.retrieve import retrieve

BROAD_QUERY = "소상공인 경영안정 자금 지원 제도"

NO_DOCS_REPORT = (
    "지금 접수 중인 지원사업 중 이 상황에 맞는 공고를 찾지 못했습니다."
    "기업마당(bizinfo.go.kr)이나 소상공인24에서 새 공고를 확인해 보세요."
)

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


def rewrite_query(state: ReportState) -> dict:
    """검색 조건을 넓혀 한 번 더 찾게 함."""
    return {"relaxed": True, "query": f"{state['query']} {BROAD_QUERY}"}


def no_docs(state: ReportState) -> dict:
    """맞는 공고가 없다고 알리고 끝낸다. LLM을 부르지 않음"""
    return {"report": NO_DOCS_REPORT,"outcome": "no_docs"}