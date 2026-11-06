"""리포트 그래프 조립. 진단 결과인 signal 하나를 넣으면 리포트 하나가 나옴."""

# START → retrieve_docs → grade_docs ─┬─ generate ─┬─ ok ──→ cross_check ─┬─ ok ──→ END
#               ↑                     │            ├─ retry → generate    ├─ retry → generate
#               └── rewrite_query ←───┤            └─ fallback ┐          └─ fallback ┐
#                                     └─ no_docs → END         fallback → END ←───────┘

from langgraph.graph import END, START, StateGraph

from app.graph import nodes as n
from app.graph.state import ReportState


def build_graph():
    """창구들을 순서대로 이어준다.
    검색 -> 선별 -> 작성 -> 감수 -> 종료
    공고 0건 → 재검색 1회 / 검사에 걸림 → 재작성 1회 → 그래도 걸리면 템플릿
    """

    # add_node(n.retrieve_docs)
    # add_edge(A, B)
    # add_conditional_edges(A, 분기함수, 표)
    g = StateGraph(ReportState)
    for node in (
        n.retrieve_docs, 
        n.grade_docs,
        n.rewrite_query,
        n.no_docs,
        n.generate,
        n.cross_check,
        n.fallback):
        g.add_node(node)

    g.add_edge(START, "retrieve_docs")
    g.add_edge("retrieve_docs", "grade_docs")
    g.add_conditional_edges("grade_docs", n.route_after_grade)
    g.add_edge("rewrite_query","retrieve_docs")
    g.add_conditional_edges("generate", n.route_after_check, {"ok":"cross_check","retry":"generate","fallback":"fallback"})
    g.add_conditional_edges("cross_check", n.route_after_check, {"ok":END,"retry":"generate","fallback":"fallback"})
    g.add_edge("no_docs",END)
    g.add_edge("fallback",END)
    return g.compile()


report_graph = build_graph()

if __name__ == "__main__":
    signal = {"risk_level":"RED","risk_type":"매출_폭락형","risk_type_confidence": 0.6, "score":30}
    state = {"signal": signal}
    for step in report_graph.stream(state, stream_mode="updates"):
        for node, update in step.items():
            print("+",node)
            state|=update #  "state 와 update 가 다른가?" -> update 내용을 state 에 합침
    print(f"\n결과: {state['outcome']} (작성 {state.get('attempts',0)}회)\n")
    print(state["report"])






    