from typing import Literal, TypedDict

MAX_ATTEMPTS = 2

# [TypeDict]
# LangGraph는 각 노드가 돌려준 dict를 상태에 덮어써서 합침.
# 그래서 검증 로직이 있는 Pydantic보다 가벼운 TypedDict로 충분
class ReportState(TypedDict, total=False):
    signal: dict                    # build_signal() 결과 — risk_type 은 여기서 꺼낸다
    query: str
    docs: list[tuple[dict, float]]
    relaxed: bool                   # rewrite_query 가 켠다. 켜지면 태그 불일치도 근거로 인정
    context: str
    report: str
    feedback: list[str]             # str → list[str]
    attempts: int
    outcome: Literal["passed", "regenerated", "fallback", "no_docs"]

