import pytest
from app.graph.nodes import grade_docs, route_after_grade, no_docs, rewrite_query
from app.graph.graph import build_graph
from app.domain.report_context import docs_context
import app.graph.nodes as n


SIGNAL = {"risk_level": "RED", "risk_type": "매출_폭락형", "risk_type_confidence": 0.6, "score": 30}


def _doc(i, tags):
    return {"doc_id": i, "title": f"공고{i}", "agency": "기관", "source_url": "u",
            "section": "지원대상", "evidence": "e", "risk_type_tags": tags}


def test_태그_불일치는_재검색으로():
    state = {"signal": SIGNAL, "docs": [(_doc(1, ["고금리_과다채무형"]), 0.03)]}
    state |= grade_docs(state)
    assert state["docs"] == [] and route_after_grade(state) == "rewrite_query"


def test_relaxed_는_태그없는_공고도_남기고_빈결과면_종료():
    state = {"signal": SIGNAL, "relaxed": True, "docs": [(_doc(1, None), 0.03)]}
    state |= grade_docs(state)
    assert len(state["docs"]) == 1 and route_after_grade(state) == "generate"
    assert route_after_grade({**state, "docs": []}) == "no_docs"


def test_재검색은_한번만_하고_없으면_종료():
    state = {"signal": SIGNAL, "query": "q", "docs": []}
    assert route_after_grade(state) == "rewrite_query"
    state |= rewrite_query(state)
    assert state["relaxed"] and state["query"].startswith("q ")
    assert route_after_grade(state) == "no_docs"      # 넓혀도 0건이면 다시 돌지 않는다
    assert no_docs(state)["outcome"] == "no_docs"


def test_두번_다_위반이면_폴백(monkeypatch):
    monkeypatch.setattr(n, "write_report", lambda ctx, fb: ("초안", ["한도 7억"]))
    state = {"signal": SIGNAL, "context": "근거", "docs": [(_doc(1, ["매출_폭락형"]), 0.03)]}
    state |= n.generate(state)
    assert n.route_after_check(state) == "retry"
    state |= n.generate(state)
    assert n.route_after_check(state) == "fallback"   # 세 번째는 없다
    state |= n.fallback(state)
    assert state["outcome"] == "fallback" and "「공고1」" in state["report"]


def test_다시_써서_감수_통과하면_regenerated(monkeypatch):
    monkeypatch.setattr(n, "verify", lambda r, c: ([], []))
    state = {"context": "근거", "report": "초안", "attempts": 2}
    state |= n.cross_check(state)
    assert n.route_after_check(state) == "ok" and state["outcome"] == "regenerated"


def test_그래프_한번에_통과(monkeypatch):
    monkeypatch.setattr(n, "retrieve", lambda q, rt: [(_doc(1, ["매출_폭락형"]), 0.03)])
    monkeypatch.setattr(n, "write_report", lambda ctx, fb: ("초안", []))
    monkeypatch.setattr(n, "verify", lambda r, c: ([], []))
    out = build_graph().invoke({"signal": SIGNAL})
    assert out["outcome"] == "passed" and out["attempts"] == 1


def test_그래프_공고없으면_LLM없이_종료(monkeypatch):
    monkeypatch.setattr(n, "retrieve", lambda q, rt: [])
    monkeypatch.setattr(n, "write_report", lambda ctx, fb: pytest.fail("LLM 을 부르면 안 된다"))
    out = build_graph().invoke({"signal": SIGNAL})
    assert out["outcome"] == "no_docs" and out["relaxed"]


def test_필수_항목은_근거에_붙는다():
    d = _doc(1, ["매출_폭락형"]) | {"must_read": "[공고1 · 신청방법] ols.semas.or.kr"}
    assert "필수 항목: [공고1 · 신청방법] ols.semas.or.kr" in docs_context([d])