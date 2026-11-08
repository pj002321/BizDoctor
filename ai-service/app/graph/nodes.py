"""리포트 그래프 노드. 상태를 받아서 바뀐 필드만 dict로 반환"""

from app.ai.report import write_report
from app.ai.verify import verify
from app.domain.report_context import build_context, fallback_report
from app.domain.signal import RISK_TYPE_QUERY
from app.graph.state import MAX_ATTEMPTS,ReportState
from app.knowledge.retrieve import retrieve

BROAD_QUERY = "소상공인 경영안정 자금 지원 제도"

NO_DOCS_REPORT = (
    "지금 접수 중인 지원사업 중 이 상황에 맞는 공고를 찾지 못했습니다."
    "기업마당(bizinfo.go.kr)이나 소상공인24에서 새 공고를 확인해 보세요."
)

def retrieve_docs(state: ReportState) -> ReportState:
    """공고 찾아오기: 검색어가 없으면 유형별로 질의를 함"""
    rt = state["signal"]["risk_type"]
    query = state.get("query") or RISK_TYPE_QUERY[rt]
    return {"query": query, "docs": retrieve(query,rt)}


def grade_docs(state: ReportState) -> ReportState:
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


def rewrite_query(state: ReportState) -> ReportState:
    """검색 조건을 넓혀 한 번 더 찾게 함."""
    return {"relaxed": True, "query": f"{state['query']} {BROAD_QUERY}"}


def no_docs(state: ReportState) -> ReportState:
    """맞는 공고가 없다고 알리고 끝낸다. LLM을 부르지 않음"""
    return {"report": NO_DOCS_REPORT,"outcome": "no_docs"}


def generate(state: ReportState) -> ReportState:
    """리포트 초안을 쓰고 숫자를 근거와 대조. 지난 위반의 내용을 빼고 다시 쓰도록함.
    이번에 생기는 위반이 새로운 feedback이 됨."""
    report, bad = write_report(state["context"], state.get("feedback"))
    return {"report":report, "feedback": bad, "attempts": state.get("attempts",0)+1}


def cross_check(state: ReportState) -> ReportState:
    """다른 LLM 모델이 주장 하나하나를 근거와 맞춰본다
    통과 -> outcome 기록 / 근거 없는 주장 -> feedback으로 기록"""
    _, bad = verify(state["report"], state["context"])
    if bad:
        return {"feedback": bad}
    return {"feedback": [], "outcome": "passed" if state["attempts"] == 1 else "regenerated"}


def fallback(state: ReportState) -> ReportState:
    """LLM 대신 템플릿 리포트로 끈낸다.
    근거 필드를 그대로 옮겨 적으므로 틀린 숫자가 나올 수 없다."""
    return {"report": fallback_report(state["signal"], [d for d,_ in state["docs"]]),"outcome":"fallback"}


def route_after_check(state: ReportState) -> str:
    """검사 결과를 보고 이후에 어디로 보낼지
    위반 없음 -> 통과 / 위반 있고 기회 남음 -> retry / 기회 다 씀 -> fallback"""
    if not state["feedback"]:
        return "ok"
    return "retry" if state["attempts"] < MAX_ATTEMPTS else "fallback"